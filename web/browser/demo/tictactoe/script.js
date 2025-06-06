class TicTacToe {
    constructor() {
        console.log('Initializing TicTacToe game...');
        this.board = Array(9).fill('');
        this.currentPlayer = 'X';
        this.gameActive = true;
        this.gameHistory = [];
        this.currentGameId = 1;
        this.scores = {
            totalGames: 0,
            wins: 0,
            losses: 0,
            ties: 0
        };

        this.initializeElements();
        this.loadGameHistory();
        this.updateScoreboard();
        this.setupEventListeners();
        console.log('Game initialized successfully');
    }

    initializeElements() {
        console.log('Initializing elements...');
        this.cells = document.querySelectorAll('.cell');
        this.newGameBtn = document.getElementById('newGameBtn');
        this.historyList = document.getElementById('historyList');
        
        console.log('Cells found:', this.cells.length);
        console.log('New Game button found:', !!this.newGameBtn);
        console.log('History list found:', !!this.historyList);
    }

    setupEventListeners() {
        console.log('Setting up event listeners...');
        this.cells.forEach(cell => {
            cell.addEventListener('click', () => this.handleCellClick(cell));
        });

        this.newGameBtn.addEventListener('click', () => {
            console.log('New Game button clicked');
            this.startNewGame();
        });
    }

    handleCellClick(cell) {
        console.log('Cell clicked:', cell.dataset.index);
        if (!this.gameActive) {
            console.log('Game is not active');
            return;
        }

        const index = cell.dataset.index;
        if (this.board[index] === '') {
            // Player's move (X)
            this.makeMove(index, 'X');
            
            if (this.checkWinner()) {
                console.log('Player won!');
                this.endGame('X');
                return;
            }

            if (this.isBoardFull()) {
                console.log('Game is a tie!');
                this.endGame('tie');
                return;
            }

            // Computer's move (O)
            setTimeout(() => {
                const emptyCells = this.board
                    .map((cell, index) => cell === '' ? index : null)
                    .filter(cell => cell !== null);
                
                if (emptyCells.length > 0) {
                    const randomIndex = emptyCells[Math.floor(Math.random() * emptyCells.length)];
                    console.log('Computer move:', randomIndex);
                    this.makeMove(randomIndex, 'O');

                    if (this.checkWinner()) {
                        console.log('Computer won!');
                        this.endGame('O');
                    } else if (this.isBoardFull()) {
                        console.log('Game is a tie!');
                        this.endGame('tie');
                    }
                }
            }, 500);
        }
    }

    makeMove(index, player) {
        console.log(`Making move: ${player} at index ${index}`);
        this.board[index] = player;
        this.cells[index].classList.add(player.toLowerCase());
    }

    checkWinner() {
        const winPatterns = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8], // Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8], // Columns
            [0, 4, 8], [2, 4, 6] // Diagonals
        ];

        return winPatterns.some(pattern => {
            const [a, b, c] = pattern;
            return this.board[a] !== '' &&
                   this.board[a] === this.board[b] &&
                   this.board[a] === this.board[c];
        });
    }

    isBoardFull() {
        return !this.board.includes('');
    }

    endGame(winner) {
        console.log('Ending game. Winner:', winner);
        this.gameActive = false;
        const gameResult = {
            id: this.currentGameId,
            board: [...this.board],
            winner: winner,
            date: new Date().toISOString()
        };

        this.gameHistory.push(gameResult);
        this.saveGameHistory();
        this.updateScoreboard(winner);
        this.updateHistoryList();
        this.currentGameId++;
    }

    startNewGame() {
        console.log('Starting new game...');
        this.board = Array(9).fill('');
        this.currentPlayer = 'X';
        this.gameActive = true;
        this.cells.forEach(cell => {
            cell.classList.remove('x', 'o');
        });
        console.log('New game started');
    }

    updateScoreboard(winner) {
        if (winner) {
            this.scores.totalGames++;
            if (winner === 'X') {
                this.scores.wins++;
            } else if (winner === 'O') {
                this.scores.losses++;
            } else {
                this.scores.ties++;
            }
        }

        document.getElementById('totalGames').textContent = this.scores.totalGames;
        document.getElementById('wins').textContent = this.scores.wins;
        document.getElementById('losses').textContent = this.scores.losses;
        document.getElementById('ties').textContent = this.scores.ties;
    }

    saveGameHistory() {
        localStorage.setItem('tictactoeHistory', JSON.stringify(this.gameHistory));
        localStorage.setItem('tictactoeScores', JSON.stringify(this.scores));
    }

    loadGameHistory() {
        const savedHistory = localStorage.getItem('tictactoeHistory');
        const savedScores = localStorage.getItem('tictactoeScores');

        if (savedHistory) {
            this.gameHistory = JSON.parse(savedHistory);
            this.currentGameId = this.gameHistory.length + 1;
        }

        if (savedScores) {
            this.scores = JSON.parse(savedScores);
        }

        this.updateHistoryList();
    }

    updateHistoryList() {
        this.historyList.innerHTML = '';
        this.gameHistory.forEach(game => {
            const gameElement = document.createElement('div');
            gameElement.className = 'history-item';
            gameElement.innerHTML = `
                <span>Game ${game.id} - ${this.getGameResultText(game.winner)}</span>
                <button class="delete-btn" data-id="${game.id}">Delete</button>
            `;

            gameElement.querySelector('.delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteGame(game.id);
            });

            gameElement.addEventListener('click', () => this.viewGame(game));
            this.historyList.appendChild(gameElement);
        });
    }

    getGameResultText(winner) {
        switch (winner) {
            case 'X': return 'You Won';
            case 'O': return 'You Lost';
            case 'tie': return 'Tie';
            default: return 'Unknown';
        }
    }

    deleteGame(gameId) {
        const gameIndex = this.gameHistory.findIndex(game => game.id === gameId);
        if (gameIndex !== -1) {
            const game = this.gameHistory[gameIndex];
            this.scores.totalGames--;
            if (game.winner === 'X') this.scores.wins--;
            else if (game.winner === 'O') this.scores.losses--;
            else this.scores.ties--;

            this.gameHistory.splice(gameIndex, 1);
            this.saveGameHistory();
            this.updateScoreboard();
            this.updateHistoryList();
        }
    }

    viewGame(game) {
        this.board = [...game.board];
        this.gameActive = false;
        this.cells.forEach((cell, index) => {
            cell.classList.remove('x', 'o');
            if (this.board[index]) {
                cell.classList.add(this.board[index].toLowerCase());
            }
        });
    }
}

// Initialize the game when the page loads
console.log('Script loaded, waiting for DOM...');
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing game...');
    new TicTacToe();
}); 