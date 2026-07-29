#!/usr/bin/env python3
"""
kuma_005_wave_prediction.py
KUMA-005: Predictive Wave Cognition Engine

پیش‌بینی آینده موج بر اساس تاریخچه:
  - R(t+Δt)
  - Risk(t+Δt)
  - Transition Probability
  - Early Warning Signals

مدل‌های پیش‌بینی:
  1. EWMA (Exponentially Weighted Moving Average)
  2. Linear Trend Extrapolation
  3. Adaptive Threshold Detection
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque

# ========================== ۱. مدل‌های داده ==========================

@dataclass
class PredictionResult:
    """نتیجه پیش‌بینی وضعیت موج"""
    current_R: float
    predicted_R: float                      # R(t+Δt)
    current_risk: float
    predicted_risk: float                   # Risk(t+Δt)
    transition_probability: float           # احتمال تغییر الگو
    predicted_pattern: str                  # الگوی پیش‌بینی‌شده
    confidence: float                       # اطمینان پیش‌بینی
    early_warning: bool                     # هشدار زودهنگام
    warning_reason: str
    metadata: Dict = field(default_factory=dict)

# ========================== ۲. موتور پیش‌بینی ==========================

class WavePredictionEngine:
    """
    موتور پیش‌بینی وضعیت موجی شبکه
    
    ورودی‌ها:
      - تاریخچه R, Risk, Variance, Out-of-phase nodes
      - وضعیت فعلی شبکه
    
    خروجی‌ها:
      - پیش‌بینی R(t+Δt)
      - پیش‌بینی Risk(t+Δt)
      - احتمال گذار فاز
      - هشدار زودهنگام
    """
    
    def __init__(self, layer, perception_engine, history_window: int = 50):
        self.layer = layer
        self.perception = perception_engine
        self.history_window = history_window
        
        # تاریخچه‌ها
        self._R_history: deque = deque(maxlen=history_window)
        self._risk_history: deque = deque(maxlen=history_window)
        self._variance_history: deque = deque(maxlen=history_window)
        self._pattern_history: deque = deque(maxlen=history_window)
        
        # پارامترهای پیش‌بینی
        self.alpha_ewma = 0.3                # ضریب EWMA
        self.trend_window = 10               # پنجره روند
        self.warning_threshold_R = 0.05      # آستانه کاهش R برای هشدار
        self.warning_threshold_risk = 0.1    # آستانه افزایش ریسک برای هشدار
    
    # ===== ۱. جمع‌آوری تاریخچه =====
    
    def update_history(self):
        """به‌روزرسانی تاریخچه از وضعیت فعلی"""
        pattern = self.perception.perceive()
        
        self._R_history.append(pattern.coherence)
        self._risk_history.append(pattern.risk_score)
        self._variance_history.append(pattern.variance)
        self._pattern_history.append(pattern.pattern_type.value)
    
    # ===== ۲. پیش‌بینی با EWMA =====
    
    def _predict_ewma(self, history: deque, steps: int = 1) -> float:
        """پیش‌بینی با میانگین متحرک نمایی"""
        if len(history) < 3:
            return history[-1] if history else 0.5
        
        # محاسبه EWMA
        ewma = history[-1]
        for val in reversed(list(history)[:-1]):
            ewma = self.alpha_ewma * val + (1 - self.alpha_ewma) * ewma
        
        # پیش‌بینی با روند EWMA
        trend = ewma - history[-1]
        return history[-1] + trend * steps
    
    # ===== ۳. پیش‌بینی با روند خطی =====
    
    def _predict_linear_trend(self, history: deque, steps: int = 1) -> float:
        """پیش‌بینی با برازش خطی ساده"""
        if len(history) < 5:
            return history[-1] if history else 0.5
        
        recent = list(history)[-self.trend_window:]
        n = len(recent)
        x = list(range(n))
        
        # محاسبه شیب
        mean_x = sum(x) / n
        mean_y = sum(recent) / n
        slope = sum((x[i] - mean_x) * (recent[i] - mean_y) for i in range(n)) / sum((x[i] - mean_x)**2 for i in range(n))
        
        # پیش‌بینی
        last_x = n - 1
        return recent[-1] + slope * steps
    
    # ===== ۴. پیش‌بینی ترکیبی =====
    
    def predict(self, steps: int = 1) -> PredictionResult:
        """
        پیش‌بینی وضعیت موج در steps گام آینده
        
        Args:
            steps: تعداد گام‌های آینده (پیش‌فرض 1)
        """
        # به‌روزرسانی تاریخچه
        self.update_history()
        
        if len(self._R_history) < 5:
            # داده کافی نیست
            current_pattern = self.perception.perceive()
            return PredictionResult(
                current_R=current_pattern.coherence,
                predicted_R=current_pattern.coherence,
                current_risk=current_pattern.risk_score,
                predicted_risk=current_pattern.risk_score,
                transition_probability=0.0,
                predicted_pattern=current_pattern.pattern_type.value,
                confidence=0.0,
                early_warning=False,
                warning_reason="insufficient_data"
            )
        
        # ۱. پیش‌بینی R
        pred_R_ewma = self._predict_ewma(self._R_history, steps)
        pred_R_trend = self._predict_linear_trend(self._R_history, steps)
        pred_R = 0.5 * pred_R_ewma + 0.5 * pred_R_trend
        pred_R = max(0, min(1, pred_R))
        
        # ۲. پیش‌بینی Risk
        pred_risk_ewma = self._predict_ewma(self._risk_history, steps)
        pred_risk_trend = self._predict_linear_trend(self._risk_history, steps)
        pred_risk = 0.5 * pred_risk_ewma + 0.5 * pred_risk_trend
        pred_risk = max(0, min(1, pred_risk))
        
        # ۳. احتمال گذار فاز
        current_R = self._R_history[-1]
        current_risk = self._risk_history[-1]
        
        # اگر R در حال کاهش و ریسک در حال افزایش است
        R_change = pred_R - current_R
        risk_change = pred_risk - current_risk
        
        transition_probability = 0.0
        if R_change < -0.05 and risk_change > 0.05:
            transition_probability = min(1, abs(R_change) * 2 + risk_change * 2)
        
        # ۴. تشخیص الگوی پیش‌بینی‌شده
        if pred_R > 0.95:
            predicted_pattern = "coherent"
        elif pred_R > 0.85:
            predicted_pattern = "stable"
        elif pred_R > 0.6:
            predicted_pattern = "converging"
        elif pred_R > 0.4:
            predicted_pattern = "transient"
        elif pred_R > 0.2:
            predicted_pattern = "collapsing"
        else:
            predicted_pattern = "chaotic"
        
        # ۵. هشدار زودهنگام
        early_warning = False
        warning_reason = ""
        
        if R_change < -self.warning_threshold_R:
            early_warning = True
            warning_reason = f"R decreasing: {R_change:.3f}"
        elif risk_change > self.warning_threshold_risk:
            early_warning = True
            warning_reason = f"Risk increasing: {risk_change:.3f}"
        elif pred_R < 0.5 and current_R > 0.7:
            early_warning = True
            warning_reason = f"Potential phase transition: R dropping below 0.5"
        
        # ۶. اطمینان پیش‌بینی
        # بر اساس همخوانی دو روش پیش‌بینی
        confidence = 1 - abs(pred_R_ewma - pred_R_trend) * 0.5
        confidence = max(0, min(1, confidence))
        
        return PredictionResult(
            current_R=current_R,
            predicted_R=pred_R,
            current_risk=current_risk,
            predicted_risk=pred_risk,
            transition_probability=transition_probability,
            predicted_pattern=predicted_pattern,
            confidence=confidence,
            early_warning=early_warning,
            warning_reason=warning_reason,
            metadata={
                "R_ewma": pred_R_ewma,
                "R_trend": pred_R_trend,
                "risk_ewma": pred_risk_ewma,
                "risk_trend": pred_risk_trend,
                "R_change": R_change,
                "risk_change": risk_change
            }
        )
    
    # ===== ۵. پیش‌بینی پروفایل کامل =====
    
    def predict_profile(self, horizon: int = 10) -> Dict:
        """
        پیش‌بینی پروفایل کامل برای افق زمانی مشخص
        
        Args:
            horizon: تعداد گام‌های آینده
        """
        R_profile = []
        risk_profile = []
        
        for step in range(1, horizon + 1):
            pred = self.predict(step)
            R_profile.append(pred.predicted_R)
            risk_profile.append(pred.predicted_risk)
        
        return {
            "horizon": horizon,
            "R_profile": R_profile,
            "risk_profile": risk_profile,
            "final_R": R_profile[-1] if R_profile else 0,
            "final_risk": risk_profile[-1] if risk_profile else 0
        }
    
    # ===== ۶. وضعیت پیش‌بینی =====
    
    def get_prediction_status(self) -> Dict:
        """
        دریافت وضعیت کامل پیش‌بینی
        """
        pred = self.predict()
        
        return {
            "prediction": {
                "current_R": pred.current_R,
                "predicted_R": pred.predicted_R,
                "current_risk": pred.current_risk,
                "predicted_risk": pred.predicted_risk,
                "transition_probability": pred.transition_probability,
                "predicted_pattern": pred.predicted_pattern,
                "confidence": pred.confidence,
                "early_warning": pred.early_warning,
                "warning_reason": pred.warning_reason
            },
            "history": {
                "R_history": list(self._R_history)[-20:],
                "risk_history": list(self._risk_history)[-20:]
            },
            "metadata": pred.metadata
        }

# ========================== ۴. تست ==========================

def run_kuma_005_test():
    """
    تست Wave Prediction Engine
    """
    print("\n" + "="*70)
    print("🧠 KUMA-005: Predictive Wave Cognition Engine")
    print("="*70 + "\n")
    
    # ۱. ایجاد شبکه
    try:
        from mother_intelligence.wave_synchronization_layer import WaveSynchronizationLayer
    except ImportError:
        from wave_synchronization_layer import WaveSynchronizationLayer
    
    from kuma_004_wave_perception import WavePerceptionEngine
    
    layer = WaveSynchronizationLayer(
        coupling_strength=2.5,
        dt=0.01,
        damping_factor=0.15
    )
    layer.create_network(num_nodes=20, topology="complete")
    
    # ۲. ایجاد ادراک و پیش‌بینی
    perception = WavePerceptionEngine(layer)
    prediction = WavePredictionEngine(layer, perception, history_window=50)
    
    print("⏳ Running prediction over 200 steps...")
    
    # اجرا و پر کردن تاریخچه
    for step in range(200):
        layer.step()
        if step % 20 == 0:
            perception.perceive()
            prediction.update_history()
    
    # ۳. پیش‌بینی نهایی
    print("\n" + "-"*50)
    print("📊 PREDICTION RESULTS")
    print("-"*50)
    
    pred_status = prediction.get_prediction_status()
    
    print(f"\n🔮 Current State:")
    print(f"   R = {pred_status['prediction']['current_R']:.4f}")
    print(f"   Risk = {pred_status['prediction']['current_risk']:.4f}")
    
    print(f"\n🔮 Prediction (next step):")
    print(f"   Predicted R = {pred_status['prediction']['predicted_R']:.4f}")
    print(f"   Predicted Risk = {pred_status['prediction']['predicted_risk']:.4f}")
    print(f"   Confidence = {pred_status['prediction']['confidence']:.4f}")
    print(f"   Predicted Pattern = {pred_status['prediction']['predicted_pattern']}")
    
    print(f"\n⚠️ Early Warning:")
    print(f"   Active: {pred_status['prediction']['early_warning']}")
    if pred_status['prediction']['early_warning']:
        print(f"   Reason: {pred_status['prediction']['warning_reason']}")
    
    print(f"\n📈 Transition Probability: {pred_status['prediction']['transition_probability']:.4f}")
    
    # ۴. پروفایل پیش‌بینی
    print("\n" + "-"*50)
    print("📈 PREDICTION PROFILE (10 steps)")
    print("-"*50)
    
    profile = prediction.predict_profile(horizon=10)
    print(f"\n   R Profile: {[f'{r:.3f}' for r in profile['R_profile']]}")
    print(f"   Risk Profile: {[f'{r:.3f}' for r in profile['risk_profile']]}")
    print(f"   Final R: {profile['final_R']:.4f}")
    print(f"   Final Risk: {profile['final_risk']:.4f}")
    
    print("\n" + "="*70)
    print("🏁 KUMA-005 Prediction Test Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_kuma_005_test()
