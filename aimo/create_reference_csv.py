"""Create reference_test.csv from the 10 AIMO3 Reference Problems."""
import csv, os

problems = [
    {
        "id": "ref_01",
        "problem": r"Alice and Bob are each holding some integer number of sweets. Alice says to Bob: 'If we each added the number of sweets we're holding to our (positive integer) age, my answer would be double yours. If we took the product, then my answer would be four times yours.' Bob replies: 'Why don't you give me five of your sweets because then both our sum and product would be equal.' What is the product of Alice and Bob's ages?",
        "answer": 50
    },
    {
        "id": "ref_02",
        "problem": r"A 500 x 500 square is divided into k rectangles, each having integer side lengths. Given that no two of these rectangles have the same perimeter, the largest possible value of k is K. What is the remainder when K is divided by 10^5?",
        "answer": 520
    },
    {
        "id": "ref_03",
        "problem": r"Let ABC be an acute-angled triangle with integer side lengths and AB < AC. Points D and E lie on segments BC and AC, respectively, such that AD = AE = AB. Line DE intersects AB at X. Circles BXD and CED intersect for the second time at Y != D. Suppose that Y lies on line AD. There is a unique such triangle with minimal perimeter. This triangle has side lengths a = BC, b = CA, and c = AB. Find the remainder when abc is divided by 10^5.",
        "answer": 336
    },
    {
        "id": "ref_04",
        "problem": r"Let f : Z_{>=1} -> Z_{>=1} be a function such that for all positive integers m and n, f(m) + f(n) = f(m + n + mn). Across all functions f such that f(n) <= 1000 for all n <= 1000, how many different values can f(2024) take?",
        "answer": 580
    },
    {
        "id": "ref_05",
        "problem": r"A tournament is held with 2^{20} runners each of which has a different running speed. In each race, two runners compete against each other with the faster runner always winning the race. The competition consists of 20 rounds with each runner starting with a score of 0. In each round, the runners are paired in such a way that in each pair, both runners have the same score at the beginning of the round. The winner of each race in the i-th round receives 2^{20-i} points and the loser gets no points. At the end of the tournament, we rank the competitors according to their scores. Let N denote the number of possible orderings of the competitors at the end of the tournament. Let k be the largest positive integer such that 10^k divides N. What is the remainder when k is divided by 10^5?",
        "answer": 21818
    },
    {
        "id": "ref_06",
        "problem": r"Define a function f : Z_{>=1} -> Z_{>=1} by f(n) = \sum_{i=1}^{n} \sum_{j=1}^{n} j^{1024} \lfloor (j + n - i)/n \rfloor. Let M = 2 * 3 * 5 * 7 * 11 * 13 and let N = f(M^{15}) - f(M^{15} - 1). Let k be the largest non-negative integer such that 2^k divides N. What is the remainder when 2^k is divided by 57?",
        "answer": 32951
    },
    {
        "id": "ref_07",
        "problem": r"Let ABC be a triangle with AB != AC, circumcircle Omega, and incircle omega. Let the contact points of omega with BC, CA, and AB be D, E, and F, respectively. Let the circumcircle of AFE meet Omega at K and let the reflection of K in EF be K'. Let N denote the foot of the perpendicular from D to EF. The circle tangent to line BN and passing through B and K intersects BC again at T != B. Let sequence (F_n)_{n>=0} be defined by F_0 = 0, F_1 = 1 and for n >= 2, F_n = F_{n-1} + F_{n-2}. Call ABC n-tastic if BD = F_n, CD = F_{n+1}, and KNK'B is cyclic. Across all n-tastic triangles, let a_n denote the maximum possible value of (CT * NB)/(BT * NE). Let alpha denote the smallest real number such that for all sufficiently large n, a_{2n} < alpha. Given that alpha = p + sqrt(q) for rationals p and q, what is the remainder when floor(p * q^p) is divided by 99991?",
        "answer": 57447
    },
    {
        "id": "ref_08",
        "problem": r"On a blackboard, Ken starts off by writing a positive integer n and then applies the following move until he first reaches 1. Given that the number on the board is m, he chooses a base b, where 2 <= b <= m, and considers the unique base-b representation of m, m = \sum_{k=0}^{\infty} a_k * b^k where a_k are non-negative integers and 0 <= a_k < b for each k. Ken then erases m on the blackboard and replaces it with \sum_{k=0}^{\infty} a_k. Across all choices of 1 <= n <= 10^{10^5}, the largest possible number of moves Ken could make is M. What is the remainder when M is divided by 10^5?",
        "answer": 32193
    },
    {
        "id": "ref_09",
        "problem": r"Let F be the set of functions alpha: Z -> Z for which there are only finitely many n in Z such that alpha(n) != 0. For two functions alpha and beta in F, define their product alpha * beta to be \sum_{n in Z} alpha(n) * beta(n). Also, for n in Z, define a shift operator S_n : F -> F by S_n(alpha)(t) = alpha(t + n) for all t in Z. A function alpha in F is called shifty if: (1) alpha(m) = 0 for all integers m < 0 and m > 8, and (2) There exists beta in F and integers k != l such that for all n in Z, S_n(alpha) * beta = 1 if n is in {k, l}, and 0 otherwise. How many shifty functions are there in F?",
        "answer": 160
    },
    {
        "id": "ref_10",
        "problem": r"Let n >= 6 be a positive integer. We call a positive integer n-Norwegian if it has three distinct positive divisors whose sum is equal to n. Let f(n) denote the smallest n-Norwegian positive integer. Let M = 3^{2025!} and for a non-negative integer c define g(c) = (1/2025!) * floor(2025! * f(M + c) / M). We can write g(0) + g(4M) + g(1848374) + g(10162574) + g(265710644) + g(44636594) = p/q where p and q are coprime positive integers. What is the remainder when p + q is divided by 99991?",
        "answer": 8687
    }
]

outpath = os.path.join(os.path.dirname(__file__), "data", "aimo3_public", "reference_test.csv")
with open(outpath, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "problem", "answer"])
    writer.writeheader()
    for p in problems:
        writer.writerow(p)

print(f"Wrote {len(problems)} problems to {outpath}")
