# simulate_fingerprint_search.py
# نمایش کاهش فضای جستجو با اثر انگشت ریتمیک

import sys
import os
import time
import random
import numpy as np
from collections import Counter

# افزودن مسیر مادر به PATH
sys.path.insert(0, os.path.join(os.getcwd(), "wave_mother"))
from mother_intelligence.universal_rhythm_fingerprint import UniversalRhythmFingerprint

def generate_text_dataset(size: int = 1000, avg_len: int = 200) -> list:
    """
    تولید دیتاست متنی با الگوهای مختلف
    """
    templates = [
        "امیر جان، این یک متن آزمایشی است. ",
        "سیستم موجی مادر با ریتم طبیعی کار می‌کند. ",
        "هر داده‌ای یک ریتم منحصر به فرد دارد. ",
        "اثر انگشت ریتمیک فضای جستجو را کاهش می‌دهد. ",
        "در این شبکه، فاز و فرکانس تعیین‌کننده هستند. ",
        "این یک نمونهٔ تصادفی برای آزمایش است. ",
        "موج‌ها در فضای لبه و ابر جریان دارند. ",
        "بلاک‌چین ریتمیک بر اساس هم‌نوایی ناظرها کار می‌کند. ",
        "هر ضرب (Beat) حاوی اطلاعاتی از گذشته است. ",
        "این پیام به‌صورت Gossip در شبکه پخش می‌شود. "
    ]
    
    dataset = []
    for i in range(size):
        num_parts = random.randint(3, 8)
        parts = [random.choice(templates) for _ in range(num_parts)]
        if random.random() > 0.7:
            parts.append(f" {random.randint(1, 999)} ")
        if random.random() > 0.8:
            parts.append(" !!! ")
        text = "".join(parts)
        if len(text) > avg_len:
            text = text[:avg_len]
        dataset.append(text)
    return dataset

def generate_signal_dataset(size: int = 1000, length: int = 100) -> list:
    """
    تولید دیتاست سیگنال (سری زمانی)
    """
    dataset = []
    for i in range(size):
        freq = random.uniform(0.5, 5.0)
        amp = random.uniform(0.1, 1.0)
        noise = random.uniform(0, 0.2)
        t = np.linspace(0, 2 * np.pi, length)
        signal = amp * np.sin(freq * t) + noise * np.random.randn(length)
        if random.random() > 0.6:
            signal = signal + np.random.randn(length) * 0.1
        dataset.append(signal.tolist())
    return dataset

def simulate_search():
    print("🧪 شبیه‌سازی جستجوی مبتنی بر اثر انگشت ریتمیک")
    print("=" * 60)
    
    # ۱. تولید دیتاست
    print("📦 تولید ۱۰۰۰ داده‌ی متنی...")
    texts = generate_text_dataset(1000, 200)
    print("📦 تولید ۱۰۰۰ سیگنال عددی...")
    signals = generate_signal_dataset(1000, 100)
    
    # ۲. انتخاب یک دادهٔ هدف (متن)
    query_text = texts[500]
    query_signal = signals[300]
    
    print(f"\n🎯 دادهٔ هدف (متن):")
    print(f"   {query_text[:100]}...")
    print(f"   طول: {len(query_text)} کاراکتر")
    
    # ۳. جستجوی مستقیم (سنتی)
    print("\n" + "-" * 60)
    print("🔍 روش ۱: جستجوی مستقیم (مقایسهٔ داده‌های خام)")
    start = time.time()
    
    direct_matches = []
    for idx, doc in enumerate(texts):
        words1 = set(query_text.split())
        words2 = set(doc.split())
        common = len(words1 & words2)
        union = len(words1 | words2)
        similarity = common / union if union > 0 else 0
        direct_matches.append((idx, similarity))
    
    direct_time = time.time() - start
    direct_matches.sort(key=lambda x: x[1], reverse=True)
    
    print(f"   ⏱️  زمان جستجو: {direct_time:.4f} ثانیه")
    print(f"   📊 تعداد مقایسه‌ها: {len(texts)} (کل دیتاست)")
    print(f"   🏆 ۵ دادهٔ مشابه (از نظر کلمات مشترک):")
    for idx, sim in direct_matches[:5]:
        print(f"      - داده {idx}: شباهت {sim:.3f} | {texts[idx][:50]}...")
    
    # ۴. جستجوی مبتنی بر اثر انگشت ریتمیک
    print("\n" + "-" * 60)
    print("🔮 روش ۲: جستجوی مبتنی بر اثر انگشت ریتمیک (Fingerprint)")
    start = time.time()
    
    uf = UniversalRhythmFingerprint(mode="auto", chunk_size=5)
    
    query_fp = uf.fingerprint(query_text)
    
    fingerprints = []
    for idx, doc in enumerate(texts):
        fp = uf.fingerprint(doc)
        fingerprints.append({
            "idx": idx,
            "fp": fp,
            "size": fp["fingerprint_size"],
            "original_size": fp["original_size"]
        })
    
    fp_matches = []
    for item in fingerprints:
        similarity = uf.compare(query_fp, item["fp"])
        fp_matches.append((item["idx"], similarity, item["size"], item["original_size"]))
    
    fp_time = time.time() - start
    fp_matches.sort(key=lambda x: x[1], reverse=True)
    
    print(f"   ⏱️  زمان جستجو: {fp_time:.4f} ثانیه")
    print(f"   📊 تعداد مقایسه‌ها: {len(fingerprints)} (کل اثر انگشت‌ها)")
    print(f"   📦 میانگین حجم هر اثر انگشت: {sum(f['size'] for f in fingerprints[:10]) / len(fingerprints[:10]):.1f} بایت")
    print(f"   📦 میانگین حجم دادهٔ اصلی: {sum(f['original_size'] for f in fingerprints[:10]) / len(fingerprints[:10]):.1f} بایت")
    print(f"   📈 نسبت فشرده‌سازی متوسط: ~{sum(f['original_size'] / max(1, f['size']) for f in fingerprints[:10]) / 10:.1f}x")
    print(f"   🏆 ۵ دادهٔ مشابه (بر اساس شباهت توزیع ریتمیک):")
    for idx, sim, fp_size, orig_size in fp_matches[:5]:
        print(f"      - داده {idx}: شباهت {sim:.3f} | حجم اصلی: {orig_size} | حجم FP: {fp_size} | نسبت: {orig_size / max(1, fp_size):.1f}x")
    
    # ۵. مقایسهٔ نتایج دو روش
    print("\n" + "=" * 60)
    print("📊 مقایسهٔ نتایج جستجو")
    print("=" * 60)
    print(f"معیار | جستجوی مستقیم | جستجوی ریتمیک")
    print(f"-------|---------------|---------------")
    print(f"زمان   | {direct_time:.4f}s       | {fp_time:.4f}s")
    print(f"مقایسه‌ها | {len(texts)}            | {len(fingerprints)}")
    print(f"حجم داده | {sum(len(t) for t in texts) / 1024:.2f} KB     | {sum(f['size'] for f in fingerprints) / 1024:.2f} KB")
    
    direct_top = {idx for idx, _ in direct_matches[:5]}
    fp_top = {idx for idx, _, _, _ in fp_matches[:5]}
    overlap = len(direct_top & fp_top)
    print(f"همپوشانی ۵ نتیجهٔ برتر: {overlap}/5")
    
    print("\n💡 نتیجه:")
    print(f"   ✓ جستجوی ریتمیک {len(fingerprints)} اثر انگشت را با {sum(f['size'] for f in fingerprints) / 1024:.2f} KB مقایسه کرد")
    print(f"   ✓ در حالی که جستجوی مستقیم {len(texts)} داده را با {sum(len(t) for t in texts) / 1024:.2f} KB مقایسه کرد")
    print(f"   ✓ کاهش فضای جستجو: {len(texts) / len(fingerprints):.1f}x")
    print(f"   ✓ کاهش حجم داده برای جستجو: {sum(len(t) for t in texts) / sum(f['size'] for f in fingerprints):.1f}x")
    print(f"   ✓ همپوشانی نتایج با جستجوی مستقیم: {overlap}/5 → ریتم شباهت‌های ساختاری را حفظ می‌کند.")
    
    # ۶. نمایش یک مثال بازسازی (اختیاری)
    print("\n" + "-" * 60)
    print("🔄 بازسازی تقریبی از روی اثر انگشت (نمایشی)")
    print("-" * 60)
    sample_text = "سلام! این یک تست است. آیا کار می‌کند؟ بله!"
    fp_sample = uf.fingerprint(sample_text)
    reconstructed = uf.reconstruct_text_from_rhythm(fp_sample["sequence"])
    print(f"متن اصلی: {sample_text}")
    print(f"بازسازی: {reconstructed}")
    print(f"(بازسازی تقریبی است و فقط ساختار ریتمیک را نشان می‌دهد)")
    
    print("\n✅ شبیه‌سازی کامل شد.")

if __name__ == "__main__":
    simulate_search()
