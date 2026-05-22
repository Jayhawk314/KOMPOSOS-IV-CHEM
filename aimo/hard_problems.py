# AIMO3 HARD PROBLEMS - True Olympiad Level
# These require genuine mathematical reasoning, not pattern matching

HARD_PROBLEMS = [
    # Number Theory - Actual Olympiad Level
    ("nt_1", "Find all positive integers n such that 2^n + 3^n is divisible by 25", None),
    ("nt_2", "What is the remainder when 7^2024 is divided by 100", None),
    ("nt_3", "Find the sum of all positive divisors of 2024", None),
    ("nt_4", "How many integers between 1 and 1000 are relatively prime to 1000", None),
    
    # Algebra - Hard
    ("alg_1", "If x + 1/x = 3, find x^5 + 1/x^5", None),
    ("alg_2", "The roots of x^3 - 6x^2 + 11x - 6 = 0 are a, b, c. Find a^2 + b^2 + c^2", None),
    ("alg_3", "Solve for x: log_2(x) + log_4(x) = 6", None),
    
    # Geometry - Olympiad
    ("geo_1", "Triangle ABC has sides 13, 14, 15. Find the area", None),
    ("geo_2", "A circle has radius 10. A chord is at distance 6 from center. Find chord length", None),
    ("geo_3", "Find the radius of the inscribed circle in a triangle with sides 5, 12, 13", None),
    
    # Combinatorics - Hard
    ("comb_1", "How many ways can 5 people sit around a circular table", None),
    ("comb_2", "In how many ways can you choose 4 books from 10 different books", None),
    ("comb_3", "How many 4-digit numbers have digits in strictly increasing order", None),
    
    # Probability - Olympiad
    ("prob_1", "Three fair dice are rolled. What is the probability the sum is 10", None),
    ("prob_2", "A card is drawn from a standard deck. What is the probability it is a face card or a heart", None),
]

print(f"Testing on {len(HARD_PROBLEMS)} hard AIMO3-style problems...")
print("These require TRUE theorem-based reasoning, not pattern matching.")
