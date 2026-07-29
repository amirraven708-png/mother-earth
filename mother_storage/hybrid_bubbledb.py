# hybrid_bubbledb.py
# معماری حافظه دو کانونی (Ellipse Memory Model)
# کانون اول: RAM (پویایی موج) | کانون دوم: دیسک (ذخیره‌سازی قطعی)

import numpy as np
import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# ============================
# کانون دوم: ذخیره‌سازی قطعی (شبیه‌سازی Room)
# ============================
@dataclass
class RhythmicFingerprint:
    """اثر انگشت ریتمیک ۵ کلاسه برای ذخیره‌سازی بلندمدت"""
    timestamp: float
    source_id: str
    sequence: List[int]           # دنبالهٔ کلاس‌ها (۵ کلاس)
    hash: str                     # هش یکتا
    coherence: float              # هم‌نوایی (۰ تا ۱)
    entropy: float                # آنتروپی
    phase_state: Dict[str, float] # وضعیت فاز در زمان ذخیره

class RoomDatabaseSimulator:
    """
    شبیه‌سازی کانون دوم (Room/SQLite) در پایتون
    """
    def __init__(self):
        self._storage: List[RhythmicFingerprint] = []
        self._index_by_hash: Dict[str, int] = {}
        
    def insert(self, fingerprint: RhythmicFingerprint) -> bool:
        """ذخیرهٔ اثر انگشت در دیتابیس"""
        if fingerprint.hash in self._index_by_hash:
            return False
        self._index_by_hash[fingerprint.hash] = len(self._storage)
        self._storage.append(fingerprint)
        return True
    
    def query_by_hash(self, hash_val: str) -> Optional[RhythmicFingerprint]:
        """جستجوی اثر انگشت بر اساس هش"""
        idx = self._index_by_hash.get(hash_val)
        if idx is None:
            return None
        return self._storage[idx]
    
    def query_by_coherence(self, min_coherence: float = 0.7) -> List[RhythmicFingerprint]:
        """دریافت اثر انگشت‌های با هم‌نوایی بالا"""
        return [fp for fp in self._storage if fp.coherence >= min_coherence]
    
    def get_all(self) -> List[RhythmicFingerprint]:
        return self._storage.copy()
    
    def count(self) -> int:
        return len(self._storage)

# ============================
# کانون اول: پویایی موج در RAM
# ============================
class InMemWaveGraph:
    """
    گراف موجی در حافظهٔ RAM برای پردازش لحظه‌ای
    """
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.phase_history: deque = deque(maxlen=max_history)
        self.frequency_history: deque = deque(maxlen=max_history)
        self._phase = 0.0
        self._frequency = 1.0
        self._stability = 0.5
        self._chaos_buffer: List[float] = []
        
    def apply_chaos(self, raw_data: Dict[str, float]) -> Dict[str, float]:
        """
        اعمال دادهٔ خام به گراف موجی و محاسبهٔ وضعیت فاز لحظه‌ای
        """
        # استخراج داده
        lambda_val = raw_data.get("lambda", 0.5)
        theta_val = raw_data.get("theta", 0.0)
        force_val = raw_data.get("force", 0.3)
        
        # به‌روزرسانی فاز (مدل Kuramoto ساده)
        self._phase = (self._phase + self._frequency * 0.1 + force_val * 0.05) % (2 * np.pi)
        self._frequency = 0.8 + 0.4 * lambda_val
        
        # ذخیره در تاریخچه
        self.phase_history.append(self._phase)
        self.frequency_history.append(self._frequency)
        
        # محاسبهٔ پایداری لحظه‌ای (بر اساس واریانس فازهای اخیر)
        if len(self.phase_history) >= 10:
            phase_std = np.std(list(self.phase_history)[-10:])
            self._stability = max(0.0, min(1.0, 1.0 - phase_std / np.pi))
        else:
            self._stability = 0.5
            
        return {
            "phase": self._phase,
            "frequency": self._frequency,
            "stability": self._stability,
            "lambda": lambda_val,
            "theta": theta_val,
            "force": force_val
        }
    
    def is_stable(self, threshold: float = 0.7) -> bool:
        """بررسی پایداری فاز (آستانهٔ اجماع)"""
        return self._stability >= threshold
    
    def get_phase_state(self) -> Dict[str, float]:
        """دریافت وضعیت فعلی فاز"""
        return {
            "phase": self._phase,
            "frequency": self._frequency,
            "stability": self._stability
        }
    
    def apply_damping(self, factor: float = 0.1):
        """
        میرایی و آزادسازی حافظهٔ RAM پس از ذخیره‌سازی
        """
        # کاهش حساسیت به نویزهای قبلی
        self._chaos_buffer = []
        # کاهش پایداری برای شروع چرخهٔ بعدی
        self._stability = max(0.3, self._stability * (1.0 - factor))
        
    def get_status(self) -> Dict:
        return {
            "phase": round(self._phase, 4),
            "frequency": round(self._frequency, 4),
            "stability": round(self._stability, 4),
            "history_len": len(self.phase_history),
            "max_history": self.max_history
        }

# ============================
# استخراج‌کننده اثر انگشت ریتمیک
# ============================
class RhythmFingerprintExtractor:
    """
    استخراج اثر انگشت ۵ کلاسه از وضعیت فاز
    """
    @staticmethod
    def extract(phase_state: Dict[str, float], source_id: str = "local") -> RhythmicFingerprint:
        """
        تبدیل وضعیت فاز به اثر انگشت ریتمیک قابل ذخیره
        """
        phase = phase_state.get("phase", 0.0)
        frequency = phase_state.get("frequency", 1.0)
        stability = phase_state.get("stability", 0.5)
        
        # نگاشت فاز به ۵ کلاس
        # کلاس‌ها: 0=گشایش, 1=زایش, 2=موج, 3=فرود, 4=سکوت
        normalized = (phase / (2 * np.pi)) % 1.0
        if normalized < 0.1:
            cls = 0
        elif normalized < 0.3:
            cls = 1
        elif normalized < 0.6:
            cls = 2
        elif normalized < 0.85:
            cls = 3
        else:
            cls = 4
            
        # تولید دنبالهٔ ۱۰ کلاسه (با تغییرات جزئی)
        sequence = []
        for i in range(10):
            shift = (normalized + i * 0.05) % 1.0
            if shift < 0.1:
                seq_cls = 0
            elif shift < 0.3:
                seq_cls = 1
            elif shift < 0.6:
                seq_cls = 2
            elif shift < 0.85:
                seq_cls = 3
            else:
                seq_cls = 4
            sequence.append(seq_cls)
            
        # محاسبهٔ coherence (شباهت به الگوی متوازن)
        from collections import Counter
        counter = Counter(sequence)
        uniform = 0.2  # 1/5
        coherence = 1.0 - sum(abs(counter.get(i, 0) / len(sequence) - uniform) for i in range(5)) / 2.0
        
        # محاسبهٔ آنتروپی
        probs = [counter.get(i, 0) / len(sequence) for i in range(5)]
        entropy = -sum(p * np.log2(p) for p in probs if p > 0)
        
        # هش یکتا
        raw = f"{source_id}:{phase}:{frequency}:{time.time()}:{sequence}"
        hash_val = hashlib.sha256(raw.encode()).hexdigest()[:16]
        
        return RhythmicFingerprint(
            timestamp=time.time(),
            source_id=source_id,
            sequence=sequence,
            hash=hash_val,
            coherence=coherence,
            entropy=entropy,
            phase_state=phase_state.copy()
        )

# ============================
# لایهٔ Repository هماهنگ‌کننده
# ============================
class BubbleDbRepository:
    """
    لایهٔ هماهنگ‌کننده بین دو کانون حافظه
    """
    def __init__(self, room_db: Optional[RoomDatabaseSimulator] = None):
        self.room_db = room_db or RoomDatabaseSimulator()
        self.memory_graph = InMemWaveGraph()
        self._stable_count = 0
        self._total_processed = 0
        
    def process_incoming_wave(self, raw_data: Dict[str, float], source_id: str = "local") -> Dict[str, Any]:
        """
        پردازش دادهٔ خام ورودی (از سنسور یا شبکه)
        """
        self._total_processed += 1
        
        # ۱. پردازش زنده در حافظه RAM
        phase_state = self.memory_graph.apply_chaos(raw_data)
        
        result = {
            "source": source_id,
            "phase_state": phase_state,
            "stable": False,
            "saved": False,
            "fingerprint": None
        }
        
        # ۲. بررسی پایداری ریتمیک (آستانهٔ اجماع)
        if self.memory_graph.is_stable(threshold=0.7):
            self._stable_count += 1
            result["stable"] = True
            
            # ۳. استخراج اثر انگشت
            fingerprint = RhythmFingerprintExtractor.extract(
                phase_state, 
                source_id=source_id
            )
            result["fingerprint"] = fingerprint
            
            # ۴. ذخیره در Room (کانون دوم)
            if self.room_db.insert(fingerprint):
                result["saved"] = True
                # ۵. میرایی و آزادسازی RAM
                self.memory_graph.apply_damping(0.15)
                
        return result
    
    def get_stable_history(self) -> List[RhythmicFingerprint]:
        """دریافت تاریخچهٔ پایدار از Room"""
        return self.room_db.get_all()
    
    def get_memory_status(self) -> Dict:
        """دریافت وضعیت کانون اول (RAM)"""
        return self.memory_graph.get_status()
    
    def get_room_status(self) -> Dict:
        """دریافت وضعیت کانون دوم (دیسک)"""
        return {
            "total_records": self.room_db.count(),
            "sample": self.room_db.get_all()[-1] if self.room_db.count() > 0 else None
        }
    
    def get_stats(self) -> Dict:
        return {
            "total_processed": self._total_processed,
            "stable_count": self._stable_count,
            "memory": self.get_memory_status(),
            "room": self.get_room_status()
        }

# ============================
# تست و نمایش
# ============================
if __name__ == "__main__":
    print("🧪 تست معماری حافظه دو کانونی (Hybrid BubbleDB)")
    print("=" * 60)
    
    # ایجاد Repository
    repo = BubbleDbRepository()
    
    # شبیه‌سازی جریان دادهٔ ورودی (۵۰ رویداد)
    print("\n📡 شبیه‌سازی جریان داده از سنسور...")
    for i in range(50):
        # تولید دادهٔ تصادفی با روند صعودی
        lambda_val = 0.3 + (i % 20) * 0.035
        theta_val = (i * 0.15) % (2 * np.pi)
        force_val = 0.2 + 0.6 * (i % 10) / 10
        
        raw = {
            "lambda": lambda_val,
            "theta": theta_val,
            "force": force_val
        }
        
        result = repo.process_incoming_wave(raw, f"sensor_{i % 3}")
        
        if i % 10 == 0:
            print(f"  رویداد {i}: فاز={result['phase_state']['phase']:.3f}, "
                  f"پایداری={result['phase_state']['stability']:.3f}, "
                  f"ذخیره={result['saved']}")
    
    # نمایش وضعیت نهایی
    print("\n" + "=" * 60)
    print("📊 وضعیت نهایی")
    print("=" * 60)
    
    stats = repo.get_stats()
    print(f"کل رویدادهای پردازش‌شده: {stats['total_processed']}")
    print(f"رویدادهای پایدار (ذخیره‌شده): {stats['stable_count']}")
    print(f"نرخ ذخیره‌سازی: {stats['stable_count'] / stats['total_processed'] * 100:.1f}%")
    print(f"\nوضعیت کانون اول (RAM):")
    print(f"  فاز: {stats['memory']['phase']}")
    print(f"  فرکانس: {stats['memory']['frequency']}")
    print(f"  پایداری: {stats['memory']['stability']}")
    print(f"  تاریخچه: {stats['memory']['history_len']}")
    print(f"\nوضعیت کانون دوم (Room):")
    print(f"  تعداد رکوردها: {stats['room']['total_records']}")
    if stats['room']['total_records'] > 0:
        fp = stats['room']['sample']
        print(f"  آخرین اثر انگشت:")
        print(f"    دنباله: {fp.sequence}")
        print(f"    هم‌نوایی: {fp.coherence:.3f}")
        print(f"    آنتروپی: {fp.entropy:.3f}")
        print(f"    هش: {fp.hash}")
    
    print("\n✅ معماری دو کانونی با موفقیت کار کرد.")
    print("   - داده‌های ناپایدار در RAM پردازش شدند.")
    print("   - داده‌های پایدار در Room ذخیره شدند.")
    print("   - RAM پس از ذخیره‌سازی میرایی شد.")
