import numpy as np
import matplotlib.pyplot as plt

# 분자: z^3 - 2z + 4  → 계수 [1, 0, -2, 4]
num = np.array([1, 0, -2, 4], dtype=float)
den = np.array([1, 0, 0, 0], dtype=float)  # z^3

# numpy로 zero 계산 (pole는 직접 안 써도 되지만 참고로 적어둠)
zeros = np.roots(num)
poles = np.roots(den)   # 세 개 모두 0 나옴

print("Zeros:", zeros)
print("Poles:", poles)

# 그림 그리기
plt.figure(figsize=(5, 5))

# 단위원
theta = np.linspace(0, 2*np.pi, 400)
plt.plot(np.cos(theta), np.sin(theta), 'k--', linewidth=1, label='Unit circle')

# zero (○) 표시
plt.scatter(zeros.real, zeros.imag, marker='o', facecolors='none', edgecolors='b', label='Zeros')

# pole (×) 표시
plt.scatter(poles.real, poles.imag, marker='x', color='r', label='Poles')

plt.axhline(0, color='black', linewidth=0.5)
plt.axvline(0, color='black', linewidth=0.5)

plt.xlim(-3, 3)
plt.ylim(-3, 3)
plt.xticks(range(-3, 4))
plt.yticks(range(-3, 4))
plt.gca().set_aspect('equal', 'box')

plt.xlabel('Real axis')
plt.ylabel('Imag axis')
plt.title('Pole-zero plot of H(z)')
plt.grid(True)
plt.legend()
plt.show()
