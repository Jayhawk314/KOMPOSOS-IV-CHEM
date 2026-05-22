"""
TIR Engine - Tool-Integrated Reasoning execution loop.

THE core component: runs the LLM with interleaved code execution.

For each solution attempt:
1. Send TIR prompt to LLM
2. LLM generates reasoning + code blocks
3. When a ```python block is detected, extract and execute the code
4. Inject the output as ```output block
5. Continue LLM generation with the output appended
6. Repeat until \\boxed{answer} or token/time limit
7. Return full trace + extracted answer

Supports two modes:
- Stop-sequence mode (vLLM): Uses stop=["```python"] to pause generation
- Post-hoc mode (hf_api, transformers): Generate full response, then
  re-run with code outputs injected for multi-turn
"""

import sys
import re
import time

sys.path.insert(0, '.')

from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

from aimo.execution_engine import CodeExecutor


@dataclass
class TIRResult:
    """Result of a single TIR solution attempt."""
    answer: Optional[int]
    trace: str                          # Full reasoning trace with code outputs
    code_blocks_executed: int           # How many code blocks were run
    code_blocks_succeeded: int          # How many ran without errors
    final_code_answer: Optional[int]    # Last successful code result
    generation_time: float
    token_count: int                    # Approximate token count

    @property
    def code_verified(self) -> bool:
        """True if code execution produced the same answer as \\boxed."""
        if self.answer is None or self.final_code_answer is None:
            return False
        return self.answer == self.final_code_answer


class TIREngine:
    """
    Tool-Integrated Reasoning engine.

    Executes LLM generation with interleaved Python code execution.
    """

    # Maximum number of code execution rounds per solution
    MAX_CODE_ROUNDS = 8

    # Maximum tokens per generation step
    MAX_TOKENS_PER_STEP = 2048

    def __init__(
        self,
        llm_engine,
        code_executor: Optional[CodeExecutor] = None,
        max_code_rounds: int = 8,
        code_timeout: float = 10.0,
        verbose: bool = False,
    ):
        """
        Args:
            llm_engine: LLMEngine instance (any backend)
            code_executor: CodeExecutor for running Python code
            max_code_rounds: Max code blocks to execute per solution
            code_timeout: Timeout per code execution in seconds
            verbose: Print debug info
        """
        self.llm = llm_engine
        self.executor = code_executor or CodeExecutor(timeout=code_timeout, verbose=verbose)
        self.max_code_rounds = max_code_rounds
        self.verbose = verbose

    def solve_once(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        time_limit: float = 60.0,
    ) -> TIRResult:
        """
        Run one TIR solution attempt.

        Uses multi-turn chat: generate response, if it contains code blocks,
        execute them, append output to conversation, and continue.

        Args:
            messages: Initial chat messages (system + user with problem)
            temperature: Sampling temperature
            time_limit: Maximum wall-clock time for this attempt

        Returns:
            TIRResult with answer, trace, and statistics
        """
        start_time = time.time()
        conversation = list(messages)
        full_trace = ""
        code_executed = 0
        code_succeeded = 0
        last_code_answer = None
        total_tokens = 0

        for round_idx in range(self.max_code_rounds + 1):
            elapsed = time.time() - start_time
            if elapsed > time_limit:
                break

            # Generate next response
            try:
                responses = self.llm.generate_chat(
                    conversation,
                    n=1,
                    temperature=temperature,
                )
                response = responses[0] if responses else ""
            except Exception as e:
                if self.verbose:
                    print(f"  [TIR] Generation error round {round_idx}: {e}", file=sys.stderr)
                break

            total_tokens += len(response) // 4  # Rough token estimate

            # Check if response has code blocks that need execution
            code_blocks = self._extract_pending_code(response)

            if not code_blocks:
                # No code to execute - this is the final response
                full_trace += response
                break

            # Execute code blocks and inject outputs
            augmented_response = self._execute_and_inject(
                response, code_blocks
            )

            for block_text, success, result in augmented_response["executions"]:
                code_executed += 1
                if success:
                    code_succeeded += 1
                    if result is not None:
                        try:
                            last_code_answer = int(result)
                        except (ValueError, TypeError):
                            pass

            full_trace += augmented_response["text"]

            # Check if we already have a boxed answer after injection
            if self._has_boxed_answer(augmented_response["text"]):
                break

            # Continue conversation with the augmented response
            conversation.append({"role": "assistant", "content": augmented_response["text"]})
            conversation.append({
                "role": "user",
                "content": "Continue your solution based on the code output above. "
                           "Give your final integer answer in \\boxed{}."
            })

        generation_time = time.time() - start_time
        answer = self._extract_boxed_answer(full_trace)

        # If no boxed answer but we have a code answer, use that
        if answer is None and last_code_answer is not None:
            answer = last_code_answer

        return TIRResult(
            answer=answer,
            trace=full_trace,
            code_blocks_executed=code_executed,
            code_blocks_succeeded=code_succeeded,
            final_code_answer=last_code_answer,
            generation_time=generation_time,
            token_count=total_tokens,
        )

    def solve_once_single_pass(
        self,
        prompt: str,
        temperature: float = 0.7,
        time_limit: float = 60.0,
    ) -> TIRResult:
        """
        Single-pass TIR: generate full response, then execute all code blocks.

        Simpler but less interactive - the LLM doesn't see code output
        during generation. Good for backends that don't support multi-turn well.

        Args:
            prompt: Complete TIR prompt string
            temperature: Sampling temperature
            time_limit: Max time

        Returns:
            TIRResult
        """
        start_time = time.time()

        try:
            responses = self.llm.generate(prompt, n=1, temperature=temperature)
            response = responses[0] if responses else ""
        except Exception as e:
            if self.verbose:
                print(f"  [TIR] Generation error: {e}", file=sys.stderr)
            return TIRResult(
                answer=None, trace="", code_blocks_executed=0,
                code_blocks_succeeded=0, final_code_answer=None,
                generation_time=time.time() - start_time, token_count=0,
            )

        # Execute all code blocks in the response
        code_blocks = self.executor.extract_code_blocks(response)
        code_executed = 0
        code_succeeded = 0
        last_code_answer = None

        for code in code_blocks:
            elapsed = time.time() - start_time
            if elapsed > time_limit:
                break
            code_executed += 1
            success, result, stderr = self.executor.execute_safely(code)
            if success:
                code_succeeded += 1
                if result is not None:
                    try:
                        last_code_answer = int(result)
                    except (ValueError, TypeError):
                        pass

        generation_time = time.time() - start_time
        answer = self._extract_boxed_answer(response)

        if answer is None and last_code_answer is not None:
            answer = last_code_answer

        return TIRResult(
            answer=answer,
            trace=response,
            code_blocks_executed=code_executed,
            code_blocks_succeeded=code_succeeded,
            final_code_answer=last_code_answer,
            generation_time=generation_time,
            token_count=len(response) // 4,
        )

    def _extract_pending_code(self, response: str) -> List[str]:
        """
        Extract Python code blocks that don't already have output blocks.

        Finds ```python...``` blocks that are NOT immediately followed by
        ```output...``` blocks.
        """
        # Find all code blocks
        code_blocks = re.findall(r'```python\s*\n(.*?)```', response, re.DOTALL)

        # Check which ones don't have output yet
        pending = []
        for block in code_blocks:
            # Check if this block already has output after it
            escaped = re.escape(block.strip()[:50])
            pattern = escaped + r'.*?```\s*\n```output'
            if not re.search(pattern, response, re.DOTALL):
                pending.append(block)

        return pending

    def _execute_and_inject(
        self,
        response: str,
        code_blocks: List[str],
    ) -> Dict:
        """
        Execute code blocks and inject output into response text.

        Returns:
            {"text": augmented response, "executions": [(code, success, result), ...]}
        """
        executions = []
        augmented = response

        for code in code_blocks:
            success, result, stderr = self.executor.execute_safely(code)
            executions.append((code, success, result))

            # Build output block
            if success:
                if result is not None:
                    output_text = str(result)
                elif stderr:
                    output_text = stderr
                else:
                    output_text = "(no output)"
            else:
                output_text = f"Error: {stderr}"

            # Inject output after the code block
            code_marker = f"```python\n{code}```"
            replacement = f"{code_marker}\n\n```output\n{output_text}\n```"
            augmented = augmented.replace(code_marker, replacement, 1)

            if self.verbose:
                status = "OK" if success else "FAIL"
                print(f"  [TIR] Code exec [{status}]: {output_text[:80]}", file=sys.stderr)

        return {"text": augmented, "executions": executions}

    def _has_boxed_answer(self, text: str) -> bool:
        """Check if text contains a \\boxed{} answer."""
        return bool(re.search(r'\\boxed\{\d+\}', text))

    def _extract_boxed_answer(self, text: str) -> Optional[int]:
        """Extract the last \\boxed{N} answer from text."""
        matches = re.findall(r'\\boxed\{(\d+)\}', text)
        if matches:
            try:
                return int(matches[-1])
            except ValueError:
                pass

        # Fallback: "answer is N" pattern
        answer_match = re.search(
            r'(?:answer|result)\s*(?:is|=|:)\s*(\d+)',
            text, re.IGNORECASE,
        )
        if answer_match:
            try:
                return int(answer_match.group(1))
            except ValueError:
                pass

        return None
