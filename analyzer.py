import re
import requests
import os
from textblob import TextBlob
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

SPAM_PATTERNS = [
    r'http[s]?://', r'check.?my.?channel', r'sub.?4.?sub',
    r'follow.?me', r'check.?my.?video', r'subscribe.?to.?me',
    r'(.)\1{4,}', r'view.?my.?channel', r'buy.?now', r'click.?here'
]

TOXIC_WORDS = [
    'hate', 'stupid', 'idiot', 'dumb', 'trash', 'garbage',
    'worst', 'terrible', 'awful', 'disgusting', 'pathetic',
    'loser', 'moron', 'scam', 'fake', 'fraud', 'ugly', 'kill'
]

def extract_video_id(url):
    patterns = [
        r'v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'embed/([a-zA-Z0-9_-]{11})'
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def fetch_comments(video_id, max_results=100):
    comments = []
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        'part': 'snippet',
        'videoId': video_id,
        'maxResults': 100,
        'order': 'relevance',
        'key': API_KEY
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'error' in data:
            return None, data['error']['message']
        for item in data.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'text': snippet['textDisplay'],
                'author': snippet['authorDisplayName'],
                'likes': snippet['likeCount'],
                'published': snippet['publishedAt']
            })
        return comments, None
    except Exception as e:
        return None, str(e)


def is_spam(text):
    text_lower = text.lower()
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_toxic(text):
    text_lower = text.lower()
    for word in TOXIC_WORDS:
        if word in text_lower:
            return True
    return False


def get_sentiment(text):
    analysis = TextBlob(text)
    score = analysis.sentiment.polarity
    if score > 0.1:
        return 'positive', score
    elif score < -0.1:
        return 'negative', score
    else:
        return 'neutral', score


def get_reply_template(comment_type):
    templates = {
        'spam': "⚠️ Please keep comments relevant to the video. Spam will be removed.",
        'toxic': "🚫 Let's keep this community respectful. Please be kind to others.",
        'question': "Great question! Check the description for more info or drop a comment below.",
        'positive': "Thank you so much! Really appreciate the support! 🙏",
        'neutral': "Thanks for watching and taking the time to comment!"
    }
    return templates.get(comment_type, templates['neutral'])


def analyze_comments(url):
    video_id = extract_video_id(url)
    if not video_id:
        return {'error': 'Invalid YouTube URL'}

    comments, error = fetch_comments(video_id)
    if error:
        return {'error': error}
    if not comments:
        return {'error': 'No comments found'}

    results = []
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    spam_count = 0
    toxic_count = 0
    best_pin_candidate = None
    best_pin_score = -1

    for c in comments:
        text = c['text']
        spam = is_spam(text)
        toxic = is_toxic(text)
        sentiment, score = get_sentiment(text)

        if spam:
            spam_count += 1
            comment_type = 'spam'
        elif toxic:
            toxic_count += 1
            comment_type = 'toxic'
        elif '?' in text:
            comment_type = 'question'
        else:
            comment_type = sentiment

        sentiment_counts[sentiment] += 1

        pin_score = c['likes'] + (score * 10)
        if not spam and not toxic and sentiment == 'positive' and pin_score > best_pin_score:
            best_pin_score = pin_score
            best_pin_candidate = c

        results.append({
            'text': text[:200],
            'author': c['author'],
            'likes': c['likes'],
            'spam': spam,
            'toxic': toxic,
            'sentiment': sentiment,
            'type': comment_type,
            'reply_template': get_reply_template(comment_type)
        })

    total = len(results)
    return {
        'total': total,
        'spam_count': spam_count,
        'toxic_count': toxic_count,
        'sentiment': sentiment_counts,
        'sentiment_pct': {
            'positive': round(sentiment_counts['positive'] / total * 100),
            'neutral': round(sentiment_counts['neutral'] / total * 100),
            'negative': round(sentiment_counts['negative'] / total * 100)
        },
        'best_pin': best_pin_candidate,
        'comments': results[:50]
    }
