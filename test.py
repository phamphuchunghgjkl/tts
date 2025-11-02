def doben(n: int) -> int:
    if n < 10:
        return 0
    tich = 1
    for ch in str(n):
        tich *= int(ch)
    return 1 + doben(tich)

t = int(input())
for _ in range(t):
    n = int(input())
    print(doben(n))
