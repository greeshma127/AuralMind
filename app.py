from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import base64
from dotenv import load_dotenv, find_dotenv
from transformers import pipeline

# Load environment variables
load_dotenv(find_dotenv())

app = Flask(__name__)
CORS(app)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")

if not CLIENT_ID or not CLIENT_SECRET or not GENIUS_ACCESS_TOKEN:
    raise ValueError("API credentials are missing. Check your .env file.")

sentiment_analyzer = pipeline("text-classification", model="nlptown/bert-base-multilingual-uncased-sentiment")

seen_songs = set()

MOOD_VARIANTS = {
    "happy": ["happy", "joyful", "cheerful", "uplifting"],
    "sad": ["sad", "melancholy", "heartbroken", "depressed"],
    "excited": ["excited", "energetic", "upbeat", "party"],
    "angry": ["angry", "frustrated", "fuming", "rage"],
    "relaxed": ["relaxed", "calm", "chill", "peaceful"],
    "bored": ["bored", "lazy", "uninspired", "dull"]
}

def get_spotify_token():
    """Fetches an access token for Spotify API."""
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)
    return response.json().get("access_token")

def get_spotify_songs_for_mood(mood, max_songs=20):
    """Fetches a large number of unique songs for a mood."""
    global seen_songs
    token = get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}

    search_terms = MOOD_VARIANTS.get(mood.lower(), [mood])
    unique_songs = []

    for term in search_terms:
        offset = 0
        while len(unique_songs) < max_songs:
            url = f"https://api.spotify.com/v1/search?q={term}&type=track&limit=50&offset={offset}"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                break  # Stop if API fails

            tracks = response.json().get("tracks", {}).get("items", [])
            if not tracks:
                break  # No more results

            for track in tracks:
                song_name = track["name"]
                artist_name = track["artists"][0]["name"]
                song_id = f"{song_name} - {artist_name}"

                if song_id not in seen_songs:  # Avoid duplicates
                    seen_songs.add(song_id)
                    unique_songs.append({"song": song_name, "artist": artist_name})

            offset += 50  # Move to the next batch

            if len(unique_songs) >= max_songs:
                break

    return unique_songs[:max_songs] if unique_songs else None

def get_lyrics(song_name, artist_name):
    """Fetches song lyrics using Genius API."""
    url = f"https://api.genius.com/search?q={song_name} {artist_name}"
    headers = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "Lyrics not found"
    
    hits = response.json().get("response", {}).get("hits", [])
    if not hits:
        return "Lyrics not found"

    song_url = hits[0]["result"]["url"]
    return f"Lyrics available at: {song_url}"

def analyze_lyrics_mood(lyrics):
    """Analyzes song lyrics to determine its mood."""
    if "Lyrics not found" in lyrics:
        return "neutral"

    result = sentiment_analyzer(lyrics[:512])
    sentiment_label = result[0]["label"]

    sentiment_to_mood = {
        "1 star": "sad",
        "2 stars": "angry",
        "3 stars": "neutral",
        "4 stars": "happy",
        "5 stars": "excited"
    }
    return sentiment_to_mood.get(sentiment_label, "neutral")

@app.route('/recommend', methods=['POST'])
def recommend():
    """Handles song recommendation based on user mood."""
    data = request.json
    user_mood = data.get("mood", "").lower()

    songs = get_spotify_songs_for_mood(user_mood, max_songs=50)

    if not songs:
        return jsonify({"error": f"No songs found for mood: {user_mood}"}), 404

    recommended_songs = []
    for song in songs:
        lyrics = get_lyrics(song["song"], song["artist"])
        song_mood = analyze_lyrics_mood(lyrics)

        if user_mood in MOOD_VARIANTS and song_mood in MOOD_VARIANTS[user_mood]:
            recommended_songs.append(f"{song['song']} by {song['artist']}")

    if not recommended_songs:
        return jsonify({"error": "No suitable songs found after filtering"}), 404

    return jsonify({"songs": recommended_songs[:3]})  # Return up to 10 songs

if __name__ == '__main__':
    app.run(debug=True)
