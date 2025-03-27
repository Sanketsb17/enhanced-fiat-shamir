from fastapi import FastAPI
from sympy import symbols, Poly
import secrets
import hashlib
import uvicorn


app = FastAPI()

# Parameters
n = 256  # Polynomial ring degree
q = 7681  # Modulus for the ring
x = symbols('x')  # Polynomial variable

def random_poly():
    """Generates a random polynomial with coefficients in Z_q."""
    coeffs = [secrets.randbelow(q) for _ in range(n)]
    return Poly(coeffs, x, domain='ZZ')

def hash_poly(poly):
    """Hashes a polynomial and reduces modulo q."""
    coeffs = poly.all_coeffs()
    poly_str = ",".join(map(str, coeffs))
    return int(hashlib.sha256(poly_str.encode()).hexdigest(), 16) % q

def reduce_poly(poly):
    """Reduces a polynomial modulo q and ensures it has exactly n coefficients."""
    coeffs = poly.all_coeffs()
    coeffs.extend([0] * (n - len(coeffs)))
    coeffs = [int(coeff) % q for coeff in coeffs]
    return Poly(coeffs[:n], x, domain='ZZ')

class EnhancedFiatShamir:
    k = 3  # Automorphism exponent

    @staticmethod
    def apply_automorphism(poly):
        """Applies an automorphism by mapping x^i → x^(ki) mod (x^n - 1)."""
        k = EnhancedFiatShamir.k
        new_coeffs = [0] * n
        for i in range(n):
            new_index = (i * k) % n
            new_coeffs[new_index] = poly.coeff_monomial(x**i) or 0
        return reduce_poly(Poly(new_coeffs, x, domain='ZZ'))

    @staticmethod
    @app.get("/keygen")
    def keygen():
        """Generates public and private keys."""
        s, A = random_poly(), random_poly()
        b = reduce_poly(A * s)
        return {
            "s": s.all_coeffs(),
            "A": A.all_coeffs(),
            "b": b.all_coeffs()
        }

    @staticmethod
    @app.post("/prove")
    def prove():
        """Prover generates proof."""
        s, A, b = EnhancedFiatShamir.keygen().values()
        s = Poly(s, x, domain='ZZ')
        A = Poly(A, x, domain='ZZ')
        b = Poly(b, x, domain='ZZ')

        r = random_poly()
        u = reduce_poly(A * r)
        u_prime = EnhancedFiatShamir.apply_automorphism(u)
        c = hash_poly(u_prime)
        z = reduce_poly(r + c * s)

        return {
            "u_prime": u_prime.all_coeffs(),
            "z": z.all_coeffs()
        }

    @staticmethod
    @app.post("/verify")
    def verify(proof: dict):
        """Verifier checks the proof."""
        A, b = EnhancedFiatShamir.keygen().values()
        A = Poly(A, x, domain='ZZ')
        b = Poly(b, x, domain='ZZ')

        u_prime = Poly(proof["u_prime"], x, domain='ZZ')
        z = Poly(proof["z"], x, domain='ZZ')

        c = hash_poly(u_prime)

        lhs = EnhancedFiatShamir.apply_automorphism(reduce_poly(A * z))
        rhs = reduce_poly(u_prime + c * EnhancedFiatShamir.apply_automorphism(b))

        return {"verified": lhs == rhs}

@app.get("/")
def home():
    return {"message": "Fiat-Shamir API is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

