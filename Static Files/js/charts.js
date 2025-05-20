/**
 * Charts and data visualization for the e-voting system
 */
class VotingCharts {
    /**
     * Create election results chart
     * @param {string} canvasId - Canvas element ID
     * @param {Array} results - Array of result objects with candidate and vote count
     */
    static createResultsChart(canvasId, results) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (!ctx) return;
        
        const labels = results.map(r => r.candidate.name);
        const data = results.map(r => r.votes);
        const totalVotes = data.reduce((sum, count) => sum + count, 0);
        
        const backgroundColors = [
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(255, 206, 86, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(255, 159, 64, 0.6)',
            'rgba(199, 199, 199, 0.6)'
        ];
        
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Votes',
                    data: data,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const percentage = totalVotes > 0 
                                    ? (value / totalVotes * 100).toFixed(2) + '%' 
                                    : '0.00%';
                                return `Votes: ${value} (${percentage})`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create voter demographics chart
     * @param {string} canvasId - Canvas element ID
     * @param {Object} data - Demographics data object
     */
    static createDemographicsChart(canvasId, data) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (!ctx) return;
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(data),
                datasets: [{
                    data: Object.values(data),
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.7)',
                        'rgba(255, 193, 7, 0.7)',
                        'rgba(23, 162, 184, 0.7)',
                        'rgba(0, 123, 255, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    /**
     * Create voting activity timeline chart
     * @param {string} canvasId - Canvas element ID
     * @param {Array} dates - Array of date strings
     * @param {Array} counts - Array of vote counts
     */
    static createActivityChart(canvasId, dates, counts) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (!ctx) return;
        
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Votes Cast',
                    data: counts,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 5
                        }
                    }
                }
            }
        });
    }
}

// Initialize charts on page load if relevant elements exist
document.addEventListener('DOMContentLoaded', function() {
    // For results page
    const resultsChart = document.getElementById('resultsChart');
    if (resultsChart) {
        // The data would normally be passed from the server
        // For demo purposes, we'll check for a results variable
        if (typeof results !== 'undefined') {
            VotingCharts.createResultsChart('resultsChart', results);
        }
    }
    
    // For admin dashboard
    const activityChart = document.getElementById('activityChart');
    if (activityChart) {
        // Generate sample dates for last 7 days
        const dates = [];
        const counts = [12, 19, 8, 15, 32, 28, 21]; // Sample data
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            dates.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
        }
        
        VotingCharts.createActivityChart('activityChart', dates, counts);
    }
});
