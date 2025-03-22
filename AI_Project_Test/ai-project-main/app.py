from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Sample mood-based song recommendations
data = {
    "Happy": ["Happy - Pharrell Williams", "Can't Stop the Feeling - Justin Timberlake"],
    "Sad": ["Someone Like You - Adele", "Fix You - Coldplay"],
    "Excited": ["Uptown Funk - Mark Ronson ft. Bruno Mars", "Don't Stop Me Now - Queen"],
    "Angry": ["Break Stuff - Limp Bizkit", "Killing In The Name - Rage Against The Machine"],
    "Relaxed": ["Weightless - Marconi Union", "Sunset Lover - Petit Biscuit"],
    "Bored": ["Counting Stars - OneRepublic", "Can't Hold Us - Macklemore & Ryan Lewis"]
}

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        request_data = request.get_json()
        mood = request_data.get("mood")
        
        if mood not in data:
            return jsonify({"error": "Mood not found"}), 404

        return jsonify({"songs": data[mood]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)