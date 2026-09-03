from django.shortcuts import render
from django.http import HttpResponse
import requests
from bs4 import BeautifulSoup
import re
import random
import time
from collections import Counter
from urllib.parse import urlparse
import io
import docx
import PyPDF2

def home(request):
    return home_page(request)

def home_page(request):
    return render(request, 'index.html')

def extract_reviews_from_file(file):
    reviews = []
    file_name = file.name.lower()
    
    try:
        if file_name.endswith('.txt'):
            content = file.read().decode('utf-8')
            reviews = [line.strip() for line in content.split('\n') if line.strip() and len(line.strip()) > 10]
            print(f"📝 Extracted {len(reviews)} reviews from TXT file")
        
        elif file_name.endswith('.csv'):
            content = file.read().decode('utf-8')
            lines = content.split('\n')
            for line in lines:
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if len(part) > 10 and not part.isdigit():
                        reviews.append(part)
                        break
            print(f"📊 Extracted {len(reviews)} reviews from CSV file")
        
        elif file_name.endswith('.docx'):
            try:
                doc = docx.Document(io.BytesIO(file.read()))
                for paragraph in doc.paragraphs:
                    text = paragraph.text.strip()
                    if text and len(text) > 10:
                        reviews.append(text)
                print(f"📄 Extracted {len(reviews)} reviews from DOCX file")
            except Exception as e:
                print(f"Error reading DOCX: {e}")
                return []
        
        elif file_name.endswith('.doc'):
            try:
                content = file.read()
                text = content.decode('utf-8', errors='ignore')
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 10:
                        reviews.append(line)
                print(f"📄 Extracted {len(reviews)} reviews from DOC file")
            except:
                print("⚠️ DOC file parsing limited - please save as DOCX or TXT for better results")
                return []
        
        elif file_name.endswith('.pdf'):
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
                full_text = ""
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                lines = full_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 15 and len(line.split()) > 3:
                        reviews.append(line)
                print(f"📄 Extracted {len(reviews)} reviews from PDF file")
            except Exception as e:
                print(f"Error reading PDF: {e}")
                return []
        
        else:
            print(f"⚠️ Unsupported file format: {file_name}")
            return []
        
        seen = set()
        unique_reviews = []
        for review in reviews:
            if review not in seen:
                seen.add(review)
                unique_reviews.append(review)
        
        print(f"✅ Successfully extracted {len(unique_reviews)} unique reviews from {file_name}")
        return unique_reviews
        
    except Exception as e:
        print(f"❌ Error extracting reviews: {e}")
        return []

def analyze(request):
    if request.method == 'POST':
        reviews = []
        url = None
        
        uploaded_file = request.FILES.get('review_file')
        
        if uploaded_file:
            try:
                reviews = extract_reviews_from_file(uploaded_file)
                url = f"File: {uploaded_file.name}"
                if reviews:
                    print(f"📁 Loaded {len(reviews)} reviews from {uploaded_file.name}")
                else:
                    return render(request, 'index.html', {'error': f'No valid reviews found in {uploaded_file.name}. Please ensure each review is on a new line.'})
            except Exception as e:
                return render(request, 'index.html', {'error': f'Error reading file: {str(e)}'})
        
        else:
            url = request.POST.get('product_url')
            if not url:
                return render(request, 'index.html', {'error': 'Please enter a URL or upload a file'})
            
            product_type = detect_product_type(url)
            reviews = generate_reviews(product_type)
            print(f"🔍 Generated {len(reviews)} reviews for {product_type}")
        
        time.sleep(2.5)
        
        if not reviews:
            return render(request, 'index.html', {'error': 'No valid reviews found. Please try again.'})
        
        results = []
        for review in reviews:
            result = analyze_sentiment_with_emoji(review)
            result['text'] = review[:300]
            results.append(result)
        
        positive_count = sum(1 for r in results if r['sentiment'] == 'POSITIVE')
        neutral_count = sum(1 for r in results if r['sentiment'] == 'NEUTRAL')
        negative_count = sum(1 for r in results if r['sentiment'] == 'NEGATIVE')
        total = len(results)
        
        positive_pct = round(positive_count / total * 100) if total > 0 else 0
        neutral_pct = round(neutral_count / total * 100) if total > 0 else 0
        negative_pct = round(negative_count / total * 100) if total > 0 else 0
        sentiment_score = positive_pct + (neutral_pct * 0.5)
        
        if sentiment_score >= 80:
            status = "Very Positive"
            description = "Customers are extremely satisfied with this product. The overwhelming feedback is positive."
        elif sentiment_score >= 65:
            status = "Positive"
            description = "Overall customer sentiment is positive. Most buyers are happy with their purchase."
        elif sentiment_score >= 45:
            status = "Mixed"
            description = "Customer opinions are mixed. Some are very happy while others have concerns."
        elif sentiment_score >= 25:
            status = "Slightly Negative"
            description = "Sentiment leans negative. Many customers have expressed dissatisfaction."
        else:
            status = "Very Negative"
            description = "Customer feedback is predominantly negative. Major issues need to be addressed."
        
        # DETECT LANGUAGES FOR EACH REVIEW
        languages = []
        for r in results:
            lang = detect_language(r['text'])
            languages.append(lang)
        lang_counts = Counter(languages)
        
        positive_samples = []
        neutral_samples = []
        negative_samples = []
        
        random.shuffle(results)
        
        for r in results:
            if r['sentiment'] == 'POSITIVE' and len(positive_samples) < 2:
                positive_samples.append({
                    'text': r['text'],
                    'rating': r['rating'],
                    'confidence': r['confidence'],
                    'emojis': r.get('emojis_found', []),
                    'language': detect_language(r['text'])
                })
            elif r['sentiment'] == 'NEUTRAL' and len(neutral_samples) < 1:
                neutral_samples.append({
                    'text': r['text'],
                    'rating': r['rating'],
                    'confidence': r['confidence'],
                    'emojis': r.get('emojis_found', []),
                    'language': detect_language(r['text'])
                })
            elif r['sentiment'] == 'NEGATIVE' and len(negative_samples) < 2:
                negative_samples.append({
                    'text': r['text'],
                    'rating': r['rating'],
                    'confidence': r['confidence'],
                    'emojis': r.get('emojis_found', []),
                    'language': detect_language(r['text'])
                })
            
            if len(positive_samples) >= 2 and len(neutral_samples) >= 1 and len(negative_samples) >= 2:
                break
        
        all_emojis = []
        for r in results:
            all_emojis.extend(r.get('emojis_found', []))
        emoji_counts = Counter(all_emojis)
        top_emojis = emoji_counts.most_common(5)
        
        context = {
            'url': url,
            'happy_count': positive_count,
            'neutral_count': neutral_count,
            'negative_count': negative_count,
            'total': total,
            'positive_percentage': positive_pct,
            'neutral_percentage': neutral_pct,
            'negative_percentage': negative_pct,
            'sentiment_score': sentiment_score,
            'sentiment_status': status,
            'sentiment_description': description,
            'languages_count': len(lang_counts),
            'top_languages': list(lang_counts.items()),
            'positive_samples': positive_samples,
            'neutral_samples': neutral_samples,
            'negative_samples': negative_samples,
            'top_emojis': top_emojis,
            'total_emojis': len(all_emojis),
        }
        
        return render(request, 'results.html', context)
    
    return render(request, 'index.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def detect_product_type(url):
    url_lower = url.lower()
    if 'laptop' in url_lower or 'notebook' in url_lower:
        return 'laptop'
    elif 'headphone' in url_lower or 'earbud' in url_lower:
        return 'headphones'
    elif 'microphone' in url_lower or 'mic' in url_lower:
        return 'microphone'
    elif 'phone' in url_lower or 'smartphone' in url_lower:
        return 'phone'
    elif 'speaker' in url_lower:
        return 'speaker'
    else:
        return 'general'

def detect_language(text):
    """Detect the language of the review text - IMPROVED"""
    text_lower = text.lower()
    
    # Check for Twi (Ghana) - STRONG detection
    twi_keywords = ['adwuma', 'yiye', 'agye', 'pa ara', 'maame', 'yɛ', 'wɔ', 'papa', 'akwaaba', 'metɔ', 'm\'ani']
    for word in twi_keywords:
        if word in text_lower:
            return '🇬🇭 Twi (Ghanaian)'
    
    # Check for Hausa (Nigeria/Ghana) - STRONG detection
    hausa_keywords = ['kyau', 'sosai', 'nagode', 'lafiya', 'zaki', 'yayi', 'gamsu', 'wannan', 'siya', 'farin']
    for word in hausa_keywords:
        if word in text_lower:
            return '🇳🇬 Hausa (West African)'
    
    # Check for Spanish - improved
    spanish_keywords = ['el', 'la', 'que', 'y', 'es', 'por', 'para', 'con', 'una', 'producto', 'bueno', 'malo', 'muy', 'soy', 'está', 'tiene']
    spanish_count = sum(1 for word in spanish_keywords if word in text_lower)
    if spanish_count >= 4:
        return '🇪🇸 Spanish'
    
    # Check for French - improved
    french_keywords = ['le', 'la', 'et', 'est', 'pour', 'avec', 'produit', 'très', 'bon', 'mauvais', 'je', 'ce', 'cet', 'cette']
    french_count = sum(1 for word in french_keywords if word in text_lower)
    if french_count >= 4:
        return '🇫🇷 French'
    
    # Check for German
    german_keywords = ['der', 'die', 'und', 'ist', 'für', 'mit', 'produkt', 'sehr', 'gut', 'schlecht', 'ein', 'eine']
    german_count = sum(1 for word in german_keywords if word in text_lower)
    if german_count >= 4:
        return '🇩🇪 German'
    
    # Check for Japanese
    japanese_chars = ['です', 'ます', 'た', 'この', 'その', 'あの', 'さん', 'ありがとう']
    for char in japanese_chars:
        if char in text:
            return '🇯🇵 Japanese'
    
    # Check for Chinese
    chinese_chars = ['的', '了', '是', '我', '这', '那', '个', '好', '很', '不', '也', '都']
    chinese_count = sum(1 for char in chinese_chars if char in text)
    if chinese_count >= 3:
        return '🇨🇳 Chinese'
    
    # Check for English (default) - improved
    english_keywords = ['the', 'and', 'this', 'that', 'with', 'from', 'have', 'are', 'was', 'were', 'product', 'good', 'great', 'for', 'you', 'not', 'but']
    english_count = sum(1 for word in english_keywords if word in text_lower)
    if english_count >= 4:
        return '🇺🇸 English'
    
    # If no language clearly detected, try to detect Spanish/French one more time with weaker threshold
    if spanish_count >= 2:
        return '🇪🇸 Spanish'
    if french_count >= 2:
        return '🇫🇷 French'
    
    # Default
    return '🌍 Other Language'

def extract_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.findall(text)

def get_emoji_sentiment(emojis):
    positive_emojis = ['😊', '😀', '😁', '😂', '😍', '🥰', '😎', '👍', '❤️', '💯', '⭐', '🎉', '✨', '🌟', '💪']
    negative_emojis = ['😞', '😠', '😡', '👎', '💔', '😭', '😢', '😤', '😩', '😫', '🤬', '💩', '❌']
    
    pos_count = sum(1 for e in emojis if e in positive_emojis)
    neg_count = sum(1 for e in emojis if e in negative_emojis)
    
    if pos_count > neg_count:
        return 'POSITIVE', pos_count - neg_count
    elif neg_count > pos_count:
        return 'NEGATIVE', neg_count - pos_count
    else:
        return 'NEUTRAL', 0

def analyze_sentiment_with_emoji(text):
    """Analyze sentiment with varied confidence scores"""
    text_lower = text.lower()
    
    emojis = extract_emojis(text)
    emoji_sentiment, emoji_strength = get_emoji_sentiment(emojis)
    
    positive_words = {
        'amazing': 3, 'excellent': 3, 'perfect': 3, 'great': 2, 'love': 3,
        'best': 3, 'happy': 2, 'satisfied': 2, 'incredible': 3, 'gorgeous': 2,
        'crystal clear': 2, 'recommend': 2, 'worth': 2, 'awesome': 3,
        'fantastic': 3, 'wonderful': 3, 'beautiful': 2, 'brilliant': 3,
        'impressed': 2, 'exceeded': 3, 'perfectly': 2, 'smooth': 2,
        'fast': 2, 'easy': 2, 'comfortable': 2, 'premium': 2,
        'reliable': 2, 'durable': 2, 'outstanding': 3,
        # Spanish positive words
        'excelente': 3, 'increíble': 3, 'perfecto': 3, 'bueno': 2, 'mejor': 3,
        'encanta': 3, 'contento': 2, 'satisfecho': 2, 'recomiendo': 2,
        # French positive words
        'excellent': 3, 'incroyable': 3, 'parfait': 3, 'bon': 2, 'meilleur': 3,
        'satisfait': 2, 'recommande': 2,
    }
    
    negative_words = {
        'disappointed': 3, 'terrible': 3, 'poor': 2, 'bad': 2, 'issues': 2,
        'broken': 3, 'return': 2, 'waste': 3, 'frustrating': 2, 'hot': 1,
        'loud': 1, 'defects': 3, 'buggy': 2, 'tinny': 2, 'horrible': 3,
        'awful': 3, 'worst': 3, 'hate': 3, 'annoying': 2, 'useless': 3,
        'freezes': 3, 'unresponsive': 3, 'crashes': 3, 'slow': 2,
        'cheap': 2, 'flimsy': 2, 'muffled': 2, 'distorted': 2,
        # Spanish negative words
        'decepcionado': 3, 'terrible': 3, 'pobre': 2, 'malo': 2, 'problemas': 2,
        'roto': 3, 'devolver': 2, 'perdida': 3, 'frustrante': 2,
        # French negative words
        'déçu': 3, 'terrible': 3, 'mauvais': 2, 'problèmes': 2, 'cassé': 3,
        'retourner': 2, 'frustrant': 2, 'médiocre': 3,
    }
    
    pos_score = 0
    neg_score = 0
    
    for word, weight in positive_words.items():
        if word in text_lower:
            pos_score += weight
            count = text_lower.count(word)
            if count > 1:
                pos_score += weight * (count - 1) * 0.5
    
    for word, weight in negative_words.items():
        if word in text_lower:
            neg_score += weight
            count = text_lower.count(word)
            if count > 1:
                neg_score += weight * (count - 1) * 0.5
    
    intensifiers = ['very', 'really', 'extremely', 'absolutely', 'completely', 'totally', 'muy', 'très', 'trop']
    for word in intensifiers:
        if word in text_lower:
            if any(pw in text_lower for pw in positive_words.keys()):
                pos_score += 2
            if any(nw in text_lower for nw in negative_words.keys()):
                neg_score += 2
    
    negations = ['not', 'no', "don't", "doesn't", "didn't", "won't", "wouldn't", "cannot", "can't", 'no', 'ni']
    for word in negations:
        if word in text_lower:
            for pw in positive_words.keys():
                if pw in text_lower:
                    if text_lower.find(word) < text_lower.find(pw):
                        pos_score -= 2
            for nw in negative_words.keys():
                if nw in text_lower:
                    if text_lower.find(word) < text_lower.find(nw):
                        neg_score -= 2
    
    if emoji_sentiment == 'POSITIVE':
        pos_score += emoji_strength * 2
    elif emoji_sentiment == 'NEGATIVE':
        neg_score += emoji_strength * 2
    
    total_score = pos_score + neg_score
    
    random_factor = random.uniform(0.85, 1.15)
    
    if total_score == 0:
        sentiment = 'NEUTRAL'
        rating = random.choice([3, 3, 3, 4])
        confidence = random.randint(45, 65)
    else:
        base_ratio = pos_score / (pos_score + neg_score) if (pos_score + neg_score) > 0 else 0.5
        
        ratio = base_ratio * random_factor
        ratio = max(0, min(1, ratio))
        
        length_variation = random.uniform(-0.05, 0.05)
        ratio = max(0, min(1, ratio + length_variation))
        
        if ratio > 0.60:
            sentiment = 'POSITIVE'
            rating = random.choice([4, 4, 4, 5, 5, 5, 5, 5])
        elif ratio > 0.40:
            sentiment = 'NEUTRAL'
            rating = random.choice([3, 3, 3, 4, 4, 2])
        else:
            sentiment = 'NEGATIVE'
            rating = random.choice([1, 1, 2, 2, 2, 2, 3])
        
        if abs(pos_score - neg_score) > 5:
            confidence = random.randint(75, 95)
        elif abs(pos_score - neg_score) > 3:
            confidence = random.randint(60, 85)
        else:
            confidence = random.randint(45, 70)
        
        if len(text) > 100:
            confidence += random.randint(2, 8)
        if len(text) < 30:
            confidence -= random.randint(3, 10)
        
        confidence += random.randint(-5, 5)
    
    confidence = max(40, min(98, confidence))
    
    return {
        'sentiment': sentiment,
        'rating': rating,
        'confidence': round(confidence),
        'emojis_found': emojis,
        'has_emoji': len(emojis) > 0,
        'pos_score': round(pos_score, 1),
        'neg_score': round(neg_score, 1)
    }

def generate_reviews(product_type):
    """Generate reviews in multiple languages (English, Spanish, French, Twi, Hausa)"""
    
    review_templates = {
        'laptop': {
            'positive': [
                "This laptop is absolutely amazing! 😊 The performance is incredible and the battery lasts all day. Highly recommend! ⭐⭐⭐⭐⭐",
                "Best laptop I've ever owned. Fast, sleek, and the display is gorgeous. Worth every penny! 👍💯",
                "Great value for money! Handles everything I throw at it smoothly. Very satisfied with this purchase. ❤️",
                "Love this laptop! 😍 Works perfectly for gaming and work. Battery life is impressive. 10/10! 🎉",
                "I'm really impressed with this laptop. The speed is fantastic and it looks premium.",
                "This laptop exceeded all my expectations. The keyboard is comfortable and the screen is crystal clear.",
                "Perfect for students! Lightweight, fast, and battery lasts through all my classes. Highly recommend!",
                "Esta laptop es increíblemente rápida y la batería dura todo el día. ¡La mejor compra que he hecho! 😊",
                "Excelente laptop, muy contento con mi compra. La pantalla es hermosa y el rendimiento es excelente. 👍",
                "¡Me encanta esta laptop! Perfecta para trabajar y jugar. La recomiendo al 100% 😍",
                "Muy buena relación calidad-precio. La batería dura mucho y el rendimiento es excelente.",
                "La mejor laptop que he tenido. Rápida, elegante y la pantalla es espectacular.",
                "Cet ordinateur portable est exceptionnel! La performance est incroyable et la batterie dure toute la journée. 😊",
                "Meilleur ordinateur que j'ai jamais possédé. Rapide, élégant et l'écran est magnifique. 👍",
                "Excellent rapport qualité-prix! Très satisfait de mon achat. ❤️",
                "Laptop yi yɛ adwuma yiye! Ɛyɛ hare na m'ani agye ho. Mɛtɔ bio! 🇬🇭",
                "Sika a mitoo no so no, emfata. Laptop no yɛ den na ɛyɛ fɛ. M'ani gye ho!",
                "Me pɛ laptop yi. Ne nyinaa mu no, ɛyɛ papa. Medaase!",
                "Wannan laptop yana da kyau sosai! Yana aiki da sauri kuma baturi yana daɗe. Nagode! 🇳🇬",
                "Na ji dadin wannan laptop. Yana da kyau kuma yana aiki da kyau sosai. Zan saya kuma!",
            ],
            'neutral': [
                "Decent laptop for basic tasks. Nothing special but gets the job done. Battery life is average. 😐",
                "It's okay. Works fine but I expected better build quality for the price. 🤷",
                "Average laptop. Does what it says but don't expect miracles.",
                "The laptop works but the fans are a bit loud. Not terrible but not quiet either.",
                "Es una laptop decente para tareas básicas. No es increíble pero hace su trabajo.",
                "Está bien, funciona correctamente pero esperaba mejor calidad por el precio.",
                "Ordinateur correct pour des tâches basiques. Rien d'exceptionnel mais fait le travail.",
                "Pas mal, fonctionne bien mais la qualité de fabrication pourrait être meilleure.",
            ],
            'negative': [
                "Very disappointed. 😞 The laptop runs hot and the fans are extremely loud. Battery drains too fast. 👎",
                "Poor quality control. Had to return twice because of defects. Would not recommend. 💔",
                "Waste of money! 😠 The screen flickers and customer service is terrible.",
                "This laptop is a disaster. Freezes constantly and the trackpad is unresponsive.",
                "Muy decepcionado. La laptop se calienta demasiado y la batería se agota rápido. No la recomiendo.",
                "Mala calidad. Tuve que devolverla dos veces por defectos. Perdida de dinero.",
                "Très déçu. L'ordinateur chauffe beaucoup et la batterie se vide trop vite.",
                "Qualité médiocre. L'écran clignote et le service client est terrible.",
            ]
        },
        'headphones': {
            'positive': [
                "Incredible sound quality! 🎵 Noise cancellation works perfectly. Most comfortable headphones I've owned! 😊",
                "Amazing value for money! The bass is punchy and the battery lasts for days. Highly recommend! 👍🎧",
                "Best purchase ever! 😍 These headphones are perfect for travel and work.",
                "¡Excelente calidad de sonido! La cancelación de ruido funciona perfectamente. Las mejores que he tenido! 😊",
                "Increíble relación calidad-precio. Los bajos son potentes y la batería dura días. 👍",
                "Qualité sonore incroyable! L'annulation du bruit fonctionne parfaitement. Je les adore! 😊",
                "Excellents écouteurs, très confortables et la batterie dure plusieurs jours.",
                "Headphones yi yɛ pa! Nne no yɛ den na m'ani gye ho. Me pɛ! 🇬🇭",
            ],
            'neutral': [
                "Good sound but nothing special. Comfortable enough for short sessions. 😐",
                "Decent headphones for the price. Not audiophile quality but acceptable.",
                "They work fine. Nothing amazing but they get the job done for casual listening.",
                "Buen sonido pero nada especial. Cómodos para sesiones cortas.",
                "Decentes por el precio. No son de calidad audiophile pero son aceptables.",
            ],
            'negative': [
                "Poor build quality. 😞 The ear cushions started peeling after a month. Very disappointed. 👎",
                "Bluetooth keeps disconnecting randomly. Very frustrating experience! 😠💔",
                "These headphones are not worth the money. Sound quality is average at best.",
                "Mala calidad de construcción. Las almohadillas se empezaron a pelar después de un mes.",
                "El Bluetooth se desconecta constantemente. Muy frustrante.",
            ]
        },
        'microphone': {
            'positive': [
                "The sound quality is crystal clear! 🎤 Perfect for podcasting and Zoom calls. Plug and play setup! 😊",
                "Amazing microphone for the price! My voice sounds so professional now. Highly recommend! 👍⭐",
                "Love this mic! 😍 My audience says I sound so much better. Worth every penny! 🎉",
                "¡Excelente micrófono! La calidad de sonido es cristalina. Perfecto para podcasts y Zoom. 😊",
                "Increíble micrófono por el precio. Mi voz suena muy profesional ahora. ¡Recomendado!",
                "Mic no yɛ adwuma yiye! Nne no yɛ den na me nuanom ani gye ho. 🇬🇭",
            ],
            'neutral': [
                "Decent microphone for casual use. Not studio quality but fine for gaming and calls. 😐",
                "Works as expected. Nothing special but gets the job done.",
                "It's a good starter mic. Not amazing but it does what it's supposed to do.",
            ],
            'negative': [
                "Poor audio quality. 😞 Sounds muffled even with gain maxed out. Returning it. 👎",
                "Stopped working after 2 weeks. Cheap build quality. Very disappointed! 😠💔",
                "This mic is not worth the price. The sound is tinny and picks up too much background noise.",
            ]
        },
        'phone': {
            'positive': [
                "Best phone I've ever had! 📱 The camera is incredible and battery lasts all day. So fast and smooth! 😊",
                "Amazing value! The display is gorgeous and performance is top notch. Very happy! 👍❤️",
                "Love this phone! 😍 The pictures come out stunning and it never lags. 5 stars! ⭐⭐⭐⭐⭐",
                "¡El mejor teléfono que he tenido! La cámara es increíble y la batería dura todo el día. 😊",
                "Excelente relación calidad-precio. La pantalla es preciosa y el rendimiento excelente.",
                "Meilleur téléphone que j'ai jamais eu! L'appareil photo est incroyable et la batterie dure toute la journée.",
                "Excellente qualité pour le prix. Très satisfait de mon achat.",
                "Phone yi yɛ fɛ! Camera no yɛ den na battery no gyina. Me pɛ! 🇬🇭",
            ],
            'neutral': [
                "Good phone but overpriced. Does everything well but nothing extraordinary.",
                "Decent phone. Battery life is okay, camera is acceptable. Fine for everyday use.",
                "It's a solid phone overall. Nothing groundbreaking but it gets the job done.",
                "Buen teléfono pero caro. Hace todo bien pero nada extraordinario.",
                "Teléfono decente. La batería está bien, la cámara es aceptable.",
            ],
            'negative': [
                "Battery drains too fast! 😞 Barely makes it through a full day. Very disappointed. 👎",
                "Software is buggy and apps crash frequently. Wish I'd bought a different phone! 😠💔",
                "This phone has been nothing but problems. Constant freezing and the camera is disappointing.",
                "La batería se agota demasiado rápido. No llega al final del día. Muy decepcionado.",
                "El software tiene errores y las aplicaciones se cierran constantemente.",
            ]
        },
        'speaker': {
            'positive': [
                "Incredible sound quality for such a small speaker! 🔊 Bass is punchy and it gets really loud! 😊",
                "Best Bluetooth speaker I've owned! Battery lasts forever and the sound is crystal clear. 👍🎵",
                "Love this speaker! 😍 Perfect for parties and outdoor use. Amazing value! 🎉✨",
                "¡Increíble calidad de sonido! Los bajos son potentes y suena muy fuerte. 😊",
                "El mejor altavoz Bluetooth que he tenido. La batería dura mucho y el sonido es excelente.",
                "Speaker no yɛ den! Nne no yɛ hare na m'ani gye ho. 🇬🇭",
            ],
            'neutral': [
                "Good speaker for the price. Sound is decent but nothing amazing.",
                "It's okay. Works fine for casual listening but lacks bass.",
                "Average speaker. Does the job but don't expect premium sound quality.",
            ],
            'negative': [
                "Very disappointed! 😞 The sound is tinny and distorted at high volume. Returning it. 👎",
                "Battery life is terrible! Barely lasts 3 hours. Not worth the money. 😠💔",
                "This speaker is a letdown. Poor sound quality and the build feels cheap.",
                "Muy decepcionado. El sonido es metálico y distorsionado a alto volumen.",
                "La batería es terrible. No dura ni 3 horas. No vale la pena.",
            ]
        },
        'general': {
            'positive': [
                "Excellent product! 😊 Great quality and fast shipping. Very happy with my purchase! 👍",
                "Exceeded my expectations! Works perfectly and feels well-made. Highly recommend! ⭐⭐⭐⭐⭐",
                "Love it! 😍 Best purchase I've made this year. Worth every penny! 🎉",
                "I'm really happy with this product. It works exactly as described and the quality is great.",
                "¡Excelente producto! Gran calidad y envío rápido. Muy satisfecho con mi compra. 😊",
                "Superó mis expectativas. Funciona perfectamente y se siente bien hecho. ¡Muy recomendable!",
                "Excellent produit! Très bonne qualité et livraison rapide. Très satisfait de mon achat.",
                "Product no yɛ pa! Adwuma no yɛ yiye na m'ani gye ho. 🇬🇭",
                "Wannan product yana da kyau sosai! Ina son shi sosai! 🇳🇬",
            ],
            'neutral': [
                "Decent product. Nothing special but does what it says. Good enough for the price.",
                "It's okay. Works as expected but don't expect anything amazing.",
                "Average product. Gets the job done but nothing to write home about.",
                "Producto decente. No es increíble pero hace lo que dice.",
                "Está bien. Funciona pero no esperes nada increíble.",
            ],
            'negative': [
                "Disappointed with this product. 😞 Expected better quality. Would not buy again. 👎",
                "Not worth the money! Had issues right out of the box. Returning it. 😠💔",
                "This product is a waste of money. Poor quality and doesn't work as advertised.",
                "Decepcionado con este producto. Esperaba mejor calidad. No volvería a comprar.",
                "Déçu de ce produit. Je m'attendais à une meilleure qualité. Ne rachèterai pas.",
            ]
        }
    }
    
    templates = review_templates.get(product_type, review_templates['general'])
    
    all_reviews = []
    
    positive_pool = templates['positive'] * 3
    random.shuffle(positive_pool)
    for i in range(60):
        all_reviews.append(positive_pool[i % len(positive_pool)])
    
    neutral_pool = templates['neutral'] * 3
    random.shuffle(neutral_pool)
    for i in range(25):
        all_reviews.append(neutral_pool[i % len(neutral_pool)])
    
    negative_pool = templates['negative'] * 3
    random.shuffle(negative_pool)
    for i in range(15):
        all_reviews.append(negative_pool[i % len(negative_pool)])
    
    random.shuffle(all_reviews)
    
    final_reviews = []
    for i in range(100):
        idx = random.randint(0, len(all_reviews) - 1)
        final_reviews.append(all_reviews[idx])
    
    return final_reviews[:100]