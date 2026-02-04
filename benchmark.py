import time
import random
import string
from lib.genalog_lcs import LCS
from lib.genalog_anchor import align_w_anchor


def generate_random_string(length):
    return "".join(random.choices(string.ascii_letters + " ", k=length))


def benchmark_lcs(length):
    s1 = generate_random_string(length)
    s2 = generate_random_string(length)

    start = time.time()
    lcs = LCS(s1, s2)
    duration = time.time() - start
    print(f"LCS (size={length}): {duration:.4f}s")


def benchmark_anchor_align(length):
    s1 = generate_random_string(length)
    # Make s2 similar to s1 to simulate real case
    s2 = list(s1)
    # Mutate 10%
    for _ in range(length // 10):
        idx = random.randint(0, length - 1)
        if random.random() < 0.5:
            s2[idx] = random.choice(string.ascii_letters)  # Subst
        else:
            # Deletion (replace with empty, handle join later) or Insert
            pass
    s2 = "".join(s2)

    start = time.time()
    res = align_w_anchor(s1, s2)
    duration = time.time() - start
    print(f"Align Anchor (size={length}): {duration:.4f}s")


if __name__ == "__main__":
    print("Benchmarking LCS...")
    for size in [100, 1000, 5000, 10000]:
        benchmark_lcs(size)

    print("\nBenchmarking Anchor Alignment...")
    for size in [100, 1000, 5000, 10000]:
        benchmark_anchor_align(size)
