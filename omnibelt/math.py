
from typing import Union, Iterable, Dict, List
import heapq


def prime_factors(n: int, /): # should probably be moved to omnibelt
    from sympy import nextprime
    # Handle edge case for n <= 1
    if n <= 1:
        raise ValueError("n must be greater than 1")
    prime = 2

    # Iterate over prime factors using sympy's nextprime function
    while prime * prime <= n:
        # While the current prime divides n, add it to the list and divide n
        while n % prime == 0:
            yield prime
            n //= prime
        # Get the next prime number
        prime = nextprime(prime)

    # If n is still greater than 2, it must be a prime number
    if n > 2:
        yield n



def closest_factors(A_factors: Union[int, Iterable[int], Dict[int, int]], B_factors: Union[int, List[int], Dict[int, int]], /):
    """
    Generate factors of A in order such that they are closest to B.

    ref: https://chatgpt.com/c/67176426-7d0c-8005-85cb-f89dc96a5db3

    Parameters:
    - A_factors: dict mapping primes to their exponents in the factorization of A
    - B_factors: dict mapping primes to their exponents in the factorization of B

    Yields:
    - factors of A in order, starting from those closest to B
    """

    if isinstance(A_factors, int):
        A_factors = prime_factors(A_factors)
    if isinstance(B_factors, int):
        B_factors = prime_factors(B_factors)
    if not isinstance(A_factors, dict):
        A_factors = Counter(A_factors)
    if not isinstance(B_factors, list):
        B_factors = Counter(B_factors)

    # Get the list of primes in A
    primes = list(A_factors.keys())
    n = len(primes)

    # Build exponent vectors for A and B
    E_A = [A_factors[p] for p in primes]
    E_B = [B_factors.get(p, 0) for p in primes]

    # Initial exponent vector: min(E_B[i], E_A[i])
    initial_e = tuple(min(E_B[i], E_A[i]) for i in range(n))

    # Compute the initial factor f = product(p_i ** e_i)
    initial_f = 1
    for p, e in zip(primes, initial_e):
        initial_f *= p ** e

    # Compute the target value B_value
    B_value = 1
    for p, e in B_factors.items():
        B_value *= p ** e

    # Compute the initial delta
    initial_delta = abs(initial_f - B_value)

    # Initialize the priority queue
    heap = []
    heapq.heappush(heap, (initial_delta, initial_f, initial_e))

    # Initialize the visited set
    visited = set()
    visited.add(initial_e)

    # Begin the search
    while heap:
        delta, f, e = heapq.heappop(heap)
        yield f  # Yield the current factor

        # Generate neighboring exponent vectors
        for i in range(n):
            e_list = list(e)

            # Try incrementing e_i if it's less than E_A[i]
            if e[i] < E_A[i]:
                e_list[i] += 1
                e_inc = tuple(e_list)
                if e_inc not in visited:
                    f_inc = f * primes[i]
                    delta_inc = abs(f_inc - B_value)
                    heapq.heappush(heap, (delta_inc, f_inc, e_inc))
                    visited.add(e_inc)

            e_list = list(e)

            # Try decrementing e_i if it's greater than 0
            if e[i] > 0:
                e_list[i] -= 1
                e_dec = tuple(e_list)
                if e_dec not in visited:
                    f_dec = f // primes[i]
                    delta_dec = abs(f_dec - B_value)
                    heapq.heappush(heap, (delta_dec, f_dec, e_dec))
                    visited.add(e_dec)


