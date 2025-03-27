from fastapi import FastAPI
import uvicorn
from sympy import symbols, Poly
import secrets
import hashlib

# Initialize FastAPI app
app = FastAPI()

# Parameters
n = 256  # Polynomial ring degree
q = 7681  # Modulus for the ring
x = symbols('x')  # Polynomial variable

def random_poly():
    coeffs = [secrets.randbelow(q) for _ in range(n)]
    return Poly(coeffs, x, domain='ZZ')

def hash_poly(poly):
    coeffs = poly.all_coeffs()
    poly_str = ",".join(map(str, coeffs))
    return int(hashlib.sha256(poly_str.encode()).hexdigest(), 16) % q

def reduce_poly(poly):
    coeffs = poly.all_coeffs()
    coeffs.extend([0] * (n - len(coeffs)))
    coeffs = [int(coeff) % q for coeff in coeffs]
    return Poly(coeffs[:n], x, domain='ZZ')

class EnhancedFiatShamir:
    k = 3  # Automorphism exponent

    @staticmethod
    def apply_automorphism(poly):
        """ Applies an automorphism by mapping x^i → x^(ki) mod (x^n - 1). """
        k = EnhancedFiatShamir.k  # Automorphism exponent
        new_coeffs = [0] * n
        for i in range(n):
            new_index = (i * k) % n  # Ensure it wraps around
            new_coeffs[new_index] = poly.coeff_monomial(x**i) or 0  # Preserve coefficients
        return reduce_poly(Poly(new_coeffs, x, domain='ZZ'))

    @staticmethod
    def keygen():
        s, A = random_poly(), random_poly()
        b = reduce_poly(A * s)
        return {"s": str(s), "A": str(A), "b": str(b)}

    @staticmethod
    def prove(s, A, b):
        r = random_poly()
        u = reduce_poly(A * r)
        u_prime = EnhancedFiatShamir.apply_automorphism(u)
        c = hash_poly(u_prime)
        z = reduce_poly(r + c * s)
        return {"u_prime": str(u_prime), "z": str(z)}

    @staticmethod
    def verify(A, b, u_prime, z):
        c = hash_poly(u_prime)
        lhs = EnhancedFiatShamir.apply_automorphism(reduce_poly(A * z))
        rhs = reduce_poly(u_prime + c * EnhancedFiatShamir.apply_automorphism(b))
        return {"verified": lhs == rhs}

# ✅ Expose the API Endpoints
@app.get("/")
def home():
    return {"message": "Fiat-Shamir API is running!"}

@app.get("/keygen")
def keygen():
    return EnhancedFiatShamir.keygen()

@app.post("/prove")
def prove(s: str, A: str, b: str):
    return EnhancedFiatShamir.prove(Poly(eval(s)), Poly(eval(A)), Poly(eval(b)))

@app.post("/verify")
def verify(A: str, b: str, u_prime: str, z: str):
    return EnhancedFiatShamir.verify(Poly(eval(A)), Poly(eval(b)), Poly(eval(u_prime)), Poly(eval(z)))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
