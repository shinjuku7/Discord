import numpy as np
import matplotlib.pyplot as plt

# Ω 축: 0 ~ π 구간
Omega = np.linspace(0, np.pi, 500)

# 주파수 응답 H(e^{jΩ}) = 1 - 2 e^{-j2Ω} + 4 e^{-j3Ω}
H = 1 - 2 * np.exp(-1j * 2 * Omega) + 4 * np.exp(-1j * 3 * Omega)
H_mag = np.abs(H)

# 대표적인 점들도 한 번 찍어 보기 (표용)
test_points = np.array([0,
                        np.pi/6,
                        np.pi/3,
                        np.pi/2,
                        2*np.pi/3,
                        5*np.pi/6,
                        np.pi])
test_vals = 1 - 2 * np.exp(-1j * 2 * test_points) + 4 * np.exp(-1j * 3 * test_points)

print("Ω (rad)    |H(e^{jΩ})|")
for w, Hv in zip(test_points, test_vals):
    print(f"{w:7.4f}   {abs(Hv):.4f}")

# 그래프 그리기
plt.figure()
plt.plot(Omega, H_mag)

# x축 눈금: 0, π/4, π/2, 3π/4, π
xticks = [0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi]
xtick_labels = ['0', 'π/4', 'π/2', '3π/4', 'π']
plt.xticks(xticks, xtick_labels)

plt.xlabel('Ω [rad/sample]')
plt.ylabel('|H(e^{jΩ})|')
plt.title('Magnitude response of H(e^{jΩ})')
plt.grid(True)
plt.ylim(0, 7)  # 대략적인 범위
plt.show()
