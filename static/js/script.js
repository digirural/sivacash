// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash-msg');

    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(() => {
                msg.remove();
            }, 500);
        }, 5000);
    });

    // Set default date to today for the input
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
    }
});
