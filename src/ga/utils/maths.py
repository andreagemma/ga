from math import log10, isclose

def dynamic_round(x, n=3): 
    v = round(x, max(0,-int(log10(x)-n))) if not isclose(x,0,abs_tol = 10**(-n-1)) else 0
    if v>10**n:
        v = int(v)
    return v
