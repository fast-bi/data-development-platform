// token-management.js

function handleTokenAndStorage() {
    var tokenKey = localStorage.getItem('tokenKey');
    if (tokenKey) {
        // Call the cleanup route
        $.ajax({
            url: '/api/v1/cleanup_cp_token',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ token_key: tokenKey }),
            headers: {
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + window.bearerToken
              }
        }).done(function(response) {
            console.log("Token cleaned up successfully");
            localStorage.removeItem('tokenKey');
        }).fail(function(xhr, status, error) {
            console.error("Error cleaning up token:", error);
        });
    }

    // Clear all items from localStorage except 'theme'
    var theme = localStorage.getItem('theme');
    localStorage.clear();
    if (theme) {
        localStorage.setItem('theme', theme);
    }
}

// Run token cleanup on page load
handleTokenAndStorage();

// Add event listener for logout button
document.addEventListener('DOMContentLoaded', function() {
    var logoutButton = document.querySelector('a[href="/logout"]');
    if (logoutButton) {
        logoutButton.addEventListener('click', function(event) {
            event.preventDefault();
            handleTokenAndStorage();
            window.location.href = this.href;
        });
    }
});

// Add event listener for page unload
window.addEventListener('beforeunload', function() {
    handleTokenAndStorage();
});