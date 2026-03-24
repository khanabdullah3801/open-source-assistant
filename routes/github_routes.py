from flask import Blueprint, jsonify
from services.github_service import get_user, get_repos, get_beginner_issues, save_user, save_repos,get_user_analytics,get_recommendations,get_smart_recommendations
from db.db import cursor
from datetime import datetime, timedelta


github_bp = Blueprint('github', __name__)

# Get user info
@github_bp.route('/user/<username>', methods=['GET'])
def user_info(username):
    user_data = get_user(username)
    repos_data = get_repos(username)
    user_id = save_user(user_data)
    save_repos(user_id, repos_data)
    return jsonify({"user": user_data, "repos_count": len(repos_data)})


# Get repos
@github_bp.route('/repos/<username>', methods=['GET'])
def repos(username):
    data = get_repos(username)
    return jsonify(data)


# Get beginner issues
@github_bp.route('/issues', methods=['GET'])
def issues():
    data = get_beginner_issues()
    return jsonify(data)

from services.github_service import get_user_analytics

@github_bp.route('/analytics/<username>', methods=['GET'])
def analytics(username):

    cursor.execute("SELECT id, last_updated FROM users WHERE username=%s", (username,))
    result = cursor.fetchone()

    needs_refresh = False

    if not result:
        needs_refresh = True
    else:
        user_id, last_updated = result

        # If data older than 6 hours → refresh
        if datetime.now() - last_updated > timedelta(hours=6):
            needs_refresh = True

    # Fetch fresh data if needed
    if needs_refresh:
        user_data = get_user(username)
        repos_data = get_repos(username)

        user_id = save_user(user_data)
        save_repos(user_id, repos_data)

    # Run analytics
    data = get_user_analytics(user_id)

    return jsonify({
        "username": username,
        "analytics": data,
        "refreshed": needs_refresh
    })


@github_bp.route('/recommend/<username>', methods=['GET'])
def recommend(username):

    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    result = cursor.fetchone()

    if not result:
        return jsonify({"error": "User not found. Run /analytics first."}), 404

    user_id = result[0]

    data = get_smart_recommendations(user_id)

    return jsonify({
        "username": username,
        "recommendations": data
    })