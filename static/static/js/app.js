document.addEventListener("DOMContentLoaded", function() {
    const alerts = document.querySelectorAll(".alert");
    if(alerts) {
        setTimeout(() => {
            alerts.forEach(alert => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            });
        }, 3000);
    }
});