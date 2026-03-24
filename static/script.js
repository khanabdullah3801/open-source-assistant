async function analyze() {
    const username = document.getElementById("username").value;

    // Fetch analytics
    const analyticsRes = await fetch(`/analytics/${username}`);
    const analyticsData = await analyticsRes.json();

    // Fetch recommendations
    const recRes = await fetch(`/recommend/${username}`);
    const recData = await recRes.json();

    // Display analytics
    document.getElementById("analytics").innerHTML = `
        <h2>📊 Analytics</h2>
        <p>Total Repos: ${analyticsData.analytics.total_repos}</p>
        <p>Total Stars: ${analyticsData.analytics.total_stars}</p>
        <p>Top Language: ${analyticsData.analytics.top_language}</p>
    `;

    // Display recommendations
    let issuesHTML = "";
    recData.recommendations.recommended_issues.forEach(issue => {
        issuesHTML += `<li><a href="${issue.url}" target="_blank">${issue.title}</a></li>`;
    });

    document.getElementById("recommendations").innerHTML = `
        <h2>💡 Recommendations</h2>
        <p>Suggested Language: ${recData.recommendations.recommended_language}</p>
        <ul>${issuesHTML}</ul>
    `;
}