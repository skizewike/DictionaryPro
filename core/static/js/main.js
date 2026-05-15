document.addEventListener('DOMContentLoaded', () => {
    const flashcard = document.getElementById('flashcard');
    const cardBack = document.getElementById('card-back');
    const ratingBtns = document.getElementById('rating-btns');
    const hint = document.querySelector('.hint');

    if (flashcard) {
        flashcard.addEventListener('click', () => {
            if (cardBack.style.display === 'none') {
                cardBack.style.display = 'flex';
                hint.style.display = 'none';
                ratingBtns.style.display = 'flex';
                flashcard.classList.add('flipped');
            }
        });
    }

    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
        setTimeout(() => {
            progressFill.style.transition = 'width 0.5s ease';
        }, 100);
    }
});