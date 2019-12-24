import random
import base64


def rabin_miller(num):
    # Miller–Rabin primary test
    s = num - 1
    t = 0
    while s % 2 == 0:
        s //= 2
        t += 1
    for trials in range(5):
        a = random.randrange(2, num - 1)
        v = pow(a, s, num)
        if v != 1:
            i = 0
            while v != (num - 1):
                if i == t - 1:
                    return False
                else:
                    i += 1
                    v = (v ** 2) % num
    return True


def is_prime(num):
    # determine if num is a prime number
    if num < 2:
        return False
    lowPrimes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101,
                 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199,
                 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
                 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443,
                 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577,
                 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701,
                 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839,
                 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983,
                 991, 997]

    if num in lowPrimes:
        return True

    for prime in lowPrimes:
        if num % prime == 0:
            return False

    return rabin_miller(num)


def generate_large_prime(keysize=2048):
    # generate a prime number with a given keysize
    while True:
        num = random.randrange(2 ** (keysize - 1), 2 ** keysize)
        if is_prime(num):
            return num


# function that return the GCD of a and b using Euclid's Algorithm
def gcd(a, b):
    while a != 0:
        a, b = b % a, a
    return b


# function that returns the modular inverse of a % m,
# which is the number x such that a*x % m = 1
def find_mod_inverse(a, m):
    # no mod inverse if a & m aren't relatively prime
    if gcd(a, m) != 1:
        return None

    # Calculate using the Extended Euclidean Algorithm:
    u1, u2, u3 = 1, 0, a
    v1, v2, v3 = 0, 1, m
    while v3 != 0:
        q = u3 // v3 # // is the integer division operator
        v1, v2, v3, u1, u2, u3 = (u1 - q * v1), (u2 - q * v2), (u3 - q * v3), v1, v2, v3
    return u1 % m


# function to decode bytes array into an integer
def str64decode(s):
    return int(base64.b64decode(s).decode('utf8'))


# function to encode a positive integer into a bytes array
def str64encode(it):
    return base64.b64encode(str(it).encode('utf8'))


def generate_rsa_key(key_size=1024):
    '''
    Known e, calculating p and q, output publicKey and privateKey in special format

    if want the e is unknown:

    p = generateLargePrime(keySize)
    q = generateLargePrime(keySize)
    n = p*q
    while True:
        e = random.randrange(2 ** (keySize - 1), 2 ** (keySize))
        if cryptomath.gcd(e, (p - 1) * (q - 1)) == 1:
            d = cryptomath.findModInverse(e, (p - 1) * (q - 1))
            break
    '''
    e = 65537
    while True:
        p = generate_large_prime(key_size)
        q = generate_large_prime(key_size)
        if gcd(e, (p - 1) * (q - 1)) == 1:
            d = find_mod_inverse(e, (p - 1) * (q - 1))
            break
    n = p * q
    publicKey = str64encode(n) + b' ' + str64encode(e)
    privateKey = str64encode(n) + b' ' + str64encode(d)

    return publicKey, privateKey
