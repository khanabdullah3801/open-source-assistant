import requests
import os
from db.db import conn, cursor  # for saving later
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")  # optional if using GitHub token
HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}

# 1. Get user info
def get_user(username):
    url = f"{BASE_URL}/users/{username}"
    response = requests.get(url, headers=HEADERS)
    return response.json()


# 2. Get user repositories
def get_repos(username):
    url = f"{BASE_URL}/users/{username}/repos"
    response = requests.get(url, headers=HEADERS)
    return response.json()


# 3. Get beginner-friendly issues (keep this!)
def get_beginner_issues():
    url = f"{BASE_URL}/search/issues?q=label:\"good first issue\"+state:open"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    return data.get("items", [])


# 4. Save user to DB
def save_user(user_data):
    cursor.execute(
        """
        INSERT INTO users (username, name, public_repos, followers, last_updated)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (username)
        DO UPDATE SET 
            name = EXCLUDED.name,
            public_repos = EXCLUDED.public_repos,
            followers = EXCLUDED.followers,
            last_updated = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (user_data['login'], user_data.get('name'), user_data['public_repos'], user_data['followers'])
    )
    conn.commit()
    return cursor.fetchone()[0]


# 5. Save repos to DB
def save_repos(user_id, repos_data):
    for repo in repos_data:
        cursor.execute(
            "INSERT INTO repos (user_id, name, language, stars) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (user_id, repo['name'], repo['language'], repo['stargazers_count'])
        )
    conn.commit()


def get_user_analytics(user_id):
    # Total repos
    cursor.execute("SELECT COUNT(*) FROM repos WHERE user_id = %s", (user_id,))
    total_repos = cursor.fetchone()[0]

    # Total stars
    cursor.execute("SELECT SUM(stars) FROM repos WHERE user_id = %s", (user_id,))
    total_stars = cursor.fetchone()[0] or 0

    # Most used language
    cursor.execute("""
        SELECT language, COUNT(*) as count
        FROM repos
        WHERE user_id = %s AND language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
        LIMIT 1
    """, (user_id,))
    
    result = cursor.fetchone()
    top_language = result[0] if result else "Unknown"

    return {
        "total_repos": total_repos,
        "total_stars": total_stars,
        "top_language": top_language
    }


def get_recommendations(user_id):
    # Get user's top language
    cursor.execute("""
        SELECT language, COUNT(*) as count
        FROM repos
        WHERE user_id = %s AND language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
        LIMIT 1
    """, (user_id,))
    
    result = cursor.fetchone()
    top_language = result[0] if result else None

    # Fetch beginner issues from GitHub
    issues = get_beginner_issues()

    # Filter issues based on language (simple matching)
    recommended_issues = []
    for issue in issues[:20]:  # limit for now
        if top_language and top_language.lower() in issue['title'].lower():
            recommended_issues.append({
                "title": issue['title'],
                "url": issue['html_url']
            })

    return {
        "recommended_language": top_language,
        "recommended_issues": recommended_issues[:5]  # top 5
    }

def get_smart_recommendations(user_id):
    from db.db import cursor
    import requests

    BASE_URL = "https://api.github.com"

    # -------------------------------
    # 1. Get user analytics
    # -------------------------------
    cursor.execute("""
        SELECT language, COUNT(*) as count
        FROM repos
        WHERE user_id = %s AND language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
        LIMIT 1
    """, (user_id,))
    
    result = cursor.fetchone()
    top_language = result[0] if result else None

    cursor.execute("SELECT COUNT(*) FROM repos WHERE user_id = %s", (user_id,))
    total_repos = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(stars) FROM repos WHERE user_id = %s", (user_id,))
    total_stars = cursor.fetchone()[0] or 0

    # -------------------------------
    # 2. Recommend repositories
    # -------------------------------
    repos_url = f"{BASE_URL}/search/repositories?q=language:{top_language}&sort=stars&order=desc"
    repos_response = requests.get(repos_url).json()

    recommended_repos = []
    for repo in repos_response.get("items", [])[:10]:
        if repo["stargazers_count"] > 100:
            recommended_repos.append({
                "name": repo["name"],
                "url": repo["html_url"],
                "stars": repo["stargazers_count"]
            })

    # -------------------------------
    # 3. Recommend issues
    # -------------------------------
    issues_url = f"{BASE_URL}/search/issues?q=label:\"good first issue\"+language:{top_language}+state:open"
    issues_response = requests.get(issues_url).json()

    recommended_issues = []
    for issue in issues_response.get("items", [])[:10]:
        recommended_issues.append({
            "title": issue["title"],
            "url": issue["html_url"]
        })

    # -------------------------------
    # 4. Next step logic
    # -------------------------------
    if total_repos < 3:
        next_step = "Build more projects before contributing to open source."
    elif total_stars < 5:
        next_step = "Try contributing to popular repositories to gain visibility."
    else:
        next_step = f"Start contributing to active {top_language} repositories."

    # -------------------------------
    # 5. Gap detection
    # -------------------------------
    gaps = []

    if total_stars == 0:
        gaps.append("Your projects have no stars. Improve visibility.")

    if total_repos > 5 and total_stars < 10:
        gaps.append("You have projects but low engagement.")

    if not top_language:
        gaps.append("No dominant programming language found.")

    return {
        "top_language": top_language,
        "recommended_repos": recommended_repos[:5],
        "recommended_issues": recommended_issues[:5],
        "next_step": next_step,
        "gaps": gaps
    }    