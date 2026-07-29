#!/usr/bin/env python3
"""
adaptive_geometry_decoder.py
ماژول دیکودر تطبیقی هندسه از روی موج جریانی
با منطق تمایز نویز از تغییر هندسه و نرخ یادگیری خودتنظیم
"""

import numpy as np
import math
from typing import Tuple

# ========================== ۱. هندسۀ پویا ==========================
class DynamicGeometry:
    """
    محیطی که پارامتر تتا (انحنای سطح) در آن ناگهان تغییر می‌کند.
    """
    def __init__(self, theta_before: float = 0.35, theta_after: float = 0.60,
                 change_time: float = 2.5):
        self.theta_before = theta_before
        self.theta_after = theta_after
        self.change_time = change_time

    def get_theta(self, t: float) -> float:
        if t < self.change_time:
            return self.theta_before
        else:
            return self.theta_after

# ========================== ۲. کانال جریانی کثیف ==========================
class StreamingWaveChannel:
    """
    شبیه‌سازی کانال انتقال موج با تأخیر (اکو)، تضعیف و نویز سفید.
    از یک بافر چرخشی برای تأخیر علّی استفاده می‌کند.
    """
    def __init__(self, delay_steps: int = 15, attenuation: float = 0.4,
                 noise_std: float = 0.15):
        self.delay_steps = delay_steps
        self.attenuation = attenuation
        self.noise_std = noise_std
        self._buffer = np.zeros(delay_steps)
        self._buf_index = 0

    def process_sample(self, y_clean: float) -> float:
        # سیگنال مستقیم + نسخۀ تأخیری تضعیف‌شده
        delayed_sample = self._buffer[self._buf_index]
        y_echo = y_clean + self.attenuation * delayed_sample
        # نویز سفید
        noise = np.random.normal(0, self.noise_std)
        y_noisy = y_echo + noise
        # به‌روزرسانی بافر چرخشی
        self._buffer[self._buf_index] = y_clean  # سیگنال اصلی برای تأخیرهای بعدی
        self._buf_index = (self._buf_index + 1) % self.delay_steps
        return y_noisy

# ========================== ۳. دیکودر تطبیقی هندسه ==========================
class AdaptiveGeometryDecoder:
    """
    تخمین زندۀ θ(t) از روی سیگنال دریافتی با نرخ یادگیری تطبیقی
    بر اساس توان خطا (Power of error).
    """
    def __init__(self, initial_theta: float = 0.3,
                 mu_min: float = 0.005, mu_max: float = 0.3,
                 gamma: float = 0.95, lambda_sens: float = 50.0,
                 omega: float = 2.0 * np.pi * 1.0):
        self.current_theta = initial_theta
        self.mu_min = mu_min
        self.mu_max = mu_max
        self.gamma = gamma          # ضریب فراموشی برای میانگین‌گیری از توان خطا
        self.lambda_sens = lambda_sens  # حساسیت تانژانت هیپربولیک
        self.omega = omega          # فرکانس حامل (برای r(t) استفاده می‌شود)
        self.Pe = 1e-6              # مقدار اولیۀ توان خطا
        # برای محاسبۀ پوشش علی: فیلتر IIR مرتبۀ اول
        self._env_alpha = 0.1       # ثابت زمانی فیلتر پوشش
        self._env_state = 0.0

    def _estimate_envelope(self, y: float) -> float:
        """تخمین پوشش لحظه‌ای با فیلتر IIR."""
        self._env_state = self._env_alpha * abs(y) + (1 - self._env_alpha) * self._env_state
        # اصلاح ضریب π/2 برای سیگنال متناوب (مثل آشکارساز پوشش ایده‌آل)
        return self._env_state * (math.pi / 2)

    def step(self, t_current: float, y_rx: float) -> Tuple[float, float]:
        """
        یک گام به‌روزرسانی θ با استفاده از مشاهدۀ نویزی.
        خروجی: (θ تخمین‌زده‌شده, μ استفاده‌شده)
        """
        # ۱. پوشش مشاهده‌شده
        A_obs = self._estimate_envelope(y_rx)

        # ۲. محاسبۀ r^2 (فاصله از مبدأ در فضای پارامتری)
        u = t_current
        v = math.sin(self.omega * t_current)
        r_sq = u**2 + v**2

        # ۳. پیش‌بینی پوشش بر اساس مدل
        A_pred = math.exp(-self.current_theta * r_sq)

        # ۴. خطای لحظه‌ای
        error = A_pred - A_obs

        # ۵. به‌روزرسانی توان خطای کوتاه‌مدت (میانگین متحرک نمایی)
        self.Pe = self.gamma * self.Pe + (1 - self.gamma) * (error**2)

        # ۶. نرخ یادگیری تطبیقی
        mu = self.mu_min + (self.mu_max - self.mu_min) * math.tanh(self.lambda_sens * self.Pe)

        # ۷. گرادیان خطا نسبت به θ
        # d(error)/dθ = - r^2 * A_pred
        gradient = - r_sq * A_pred
        # بنابراین آپدیت: θ ← θ - μ * (error) * (dA_pred/dθ) = θ - μ * error * (- r^2 * A_pred)
        # = θ + μ * error * r^2 * A_pred
        self.current_theta += mu * error * r_sq * A_pred

        # محدود کردن θ به بازۀ معقول (مثبت)
        if self.current_theta < 0.01:
            self.current_theta = 0.01
        elif self.current_theta > 1.5:
            self.current_theta = 1.5

        return self.current_theta, mu

# ========================== ۴. اسکریپت تست ==========================
if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')  # برای محیط بدون نمایشگر
    import matplotlib.pyplot as plt

    # تنظیمات شبیه‌سازی
    fs = 100            # نرخ نمونه‌برداری (Hz)
    duration = 6.0      # ثانیه
    t = np.arange(0, duration, 1/fs)
    omega_carrier = 2.0 * np.pi * 5.0   # فرکانس حامل موج
    omega_geom = 2.0 * np.pi * 1.0      # فرکانس v(t) در محاسبۀ r^2

    # هندسۀ پویا
    geometry = DynamicGeometry(theta_before=0.35, theta_after=0.60, change_time=2.5)

    # کانال
    channel = StreamingWaveChannel(delay_steps=15, attenuation=0.4, noise_std=0.15)

    # دیکودر
    decoder = AdaptiveGeometryDecoder(initial_theta=0.3,
                                      mu_min=0.005, mu_max=0.3,
                                      gamma=0.95, lambda_sens=50.0,
                                      omega=omega_geom)

    # تاریخچه
    theta_true = []
    theta_est = []
    mu_hist = []
    y_clean_hist = []
    y_noisy_hist = []
    A_true_hist = []

    for i, ti in enumerate(t):
        # تتا واقعی
        theta_t = geometry.get_theta(ti)
        theta_true.append(theta_t)

        # محاسبۀ r^2
        u = ti
        v = math.sin(omega_geom * ti)
        r_sq = u**2 + v**2

        # پوشش واقعی (فرستنده)
        A_tx = math.exp(-theta_t * r_sq)
        A_true_hist.append(A_tx)

        # سیگنال تمیز (حامل مدوله‌شده)
        y_clean = A_tx * math.sin(omega_carrier * ti)
        y_clean_hist.append(y_clean)

        # عبور از کانال
        y_noisy = channel.process_sample(y_clean)
        y_noisy_hist.append(y_noisy)

        # یک گام تخمین
        th_est, mu_val = decoder.step(ti, y_noisy)
        theta_est.append(th_est)
        mu_hist.append(mu_val)

    # رسم نمودارها
    fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True)
    fig.suptitle("Adaptive Geometry Decoder — تشخیص تغییر هندسه از موج نویزی")

    # ۱. تتا واقعی و تخمین‌زده‌شده
    axes[0].plot(t, theta_true, 'k--', linewidth=2, label=r'$\theta_{\rm true}$')
    axes[0].plot(t, theta_est, 'b', linewidth=1.5, label=r'$\theta_{\rm est}$')
    axes[0].set_ylabel(r'$\theta$')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # ۲. نرخ یادگیری μ(t)
    axes[1].plot(t, mu_hist, 'r', linewidth=1.5)
    axes[1].set_ylabel(r'$\mu(t)$')
    axes[1].set_title('نرخ یادگیری تطبیقی (واکنش به شوک)')
    axes[1].grid(True, alpha=0.3)

    # ۳. پوشش واقعی (زمینه) و سیگنال نویزی
    axes[2].plot(t, A_true_hist, 'g', alpha=0.8, label='پوشش واقعی')
    axes[2].plot(t, y_noisy_hist, color='gray', alpha=0.5, label='سیگنال دریافتی')
    axes[2].set_ylabel('دامنه')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    # ۴. خطای تخمین θ
    axes[3].plot(t, np.abs(np.array(theta_est) - np.array(theta_true)), 'm', linewidth=1.5)
    axes[3].set_ylabel(r'$|\theta_{\rm est} - \theta_{\rm true}|$')
    axes[3].set_xlabel('زمان (ثانیه)')
    axes[3].grid(True, alpha=0.3)
    axes[3].set_title('خطای مطلق تخمین')

    plt.tight_layout()
    plt.savefig("adaptive_geometry_decoder_output.png", dpi=150)
    print("✅ نمودار در adaptive_geometry_decoder_output.png ذخیره شد.")

    # خروجی متنی برای نقاط کلیدی
    idx_change = np.searchsorted(t, 2.5)
    print(f"\nلحظۀ پرش: t = 2.5 s")
    print(f"θ واقعی قبل از پرش: {theta_true[idx_change-1]:.3f}")
    print(f"θ تخمینی درست قبل از پرش: {theta_est[idx_change-1]:.3f}")
    print(f"μ در همان لحظه: {mu_hist[idx_change-1]:.4f}")
    print(f"\nبعد از پرش (t≈2.6): θ تخمینی = {theta_est[int(2.6*fs)]:.3f}, μ = {mu_hist[int(2.6*fs)]:.4f}")
    print(f"در انتها (t≈5.9): θ تخمینی = {theta_est[-1]:.3f}, μ = {mu_hist[-1]:.4f}")
