/**
 * Blockchain visualization for the admin dashboard
 */
class BlockchainVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.blockchain = [];
    }
    
    /**
     * Fetch blockchain data from the server
     */
    async fetchBlockchain() {
        try {
            const response = await fetch('/api/blockchain');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            this.blockchain = await response.json();
            this.render();
        } catch (error) {
            console.error('Error fetching blockchain:', error);
            this.renderError(error.message);
        }
    }
    
    /**
     * Render the blockchain visualization
     */
    render() {
        if (!this.container) {
            console.error('Container not found');
            return;
        }
        
        if (!this.blockchain || this.blockchain.length === 0) {
            this.container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>No blockchain data available.
                </div>
            `;
            return;
        }
        
        let html = '<div class="blockchain-wrapper">';
        
        // Create visual representation of blockchain
        this.blockchain.forEach((block, index) => {
            const isGenesisBlock = index === 0;
            const hasTransactions = block.data && block.data.length > 0;
            
            html += `
                <div class="card mb-3 ${isGenesisBlock ? 'border-success' : ''}">
                    <div class="card-header bg-dark text-light d-flex justify-content-between align-items-center">
                        <span><i class="fas fa-cube me-2"></i>Block #${block.index}</span>
                        <span class="small">${new Date(block.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Hash:</strong><br><code class="small">${block.hash}</code></p>
                                <p><strong>Previous Hash:</strong><br><code class="small">${block.previous_hash}</code></p>
                                <p><strong>Nonce:</strong> ${block.nonce}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Data:</strong></p>
                                <div class="bg-light p-2 rounded" style="max-height: 150px; overflow-y: auto;">
                                    ${hasTransactions ? this.renderTransactions(block.data) : '<p class="text-muted">No data (Genesis Block)</p>'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                ${index < this.blockchain.length - 1 ? this.renderChainConnector() : ''}
            `;
        });
        
        html += '</div>';
        this.container.innerHTML = html;
    }
    
    /**
     * Render transactions within a block
     * @param {Array} transactions - Transaction data
     * @returns {string} HTML representation of transactions
     */
    renderTransactions(transactions) {
        if (!transactions || transactions.length === 0) {
            return '<p class="text-muted">No transactions</p>';
        }
        
        let html = '';
        transactions.forEach(tx => {
            html += `
                <div class="transaction-item mb-2 p-2 border-bottom">
                    <div><strong>User ID:</strong> ${tx.user_id}</div>
                    <div><strong>Candidate ID:</strong> ${tx.candidate_id}</div>
                    <div><strong>Election ID:</strong> ${tx.election_id}</div>
                    <div><strong>Time:</strong> ${new Date(tx.timestamp).toLocaleString()}</div>
                </div>
            `;
        });
        
        return html;
    }
    
    /**
     * Render connector between blocks
     * @returns {string} HTML for block connector
     */
    renderChainConnector() {
        return `
            <div class="text-center mb-3">
                <i class="fas fa-link"></i>
            </div>
        `;
    }
    
    /**
     * Render error message
     * @param {string} message - Error message
     */
    renderError(message) {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>Error loading blockchain data: ${message}
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const blockchainBtn = document.getElementById('show-blockchain');
    if (blockchainBtn) {
        const visualizer = new BlockchainVisualizer('blockchain-visualization');
        
        blockchainBtn.addEventListener('click', () => {
            const container = document.getElementById('blockchain-visualization');
            
            if (container.style.display === 'none') {
                container.style.display = 'block';
                visualizer.fetchBlockchain();
            } else {
                container.style.display = 'none';
            }
        });
    }
});
