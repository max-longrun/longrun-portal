// Main JavaScript for LeadGen Analytics Dashboard

// Chart instances
// Chart instances will be declared in their update functions

// Current time frame
let currentTimeframe = 'mtd';
let customStartDate = null;
let customEndDate = null;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeTimeframeButtons();
    fetchDashboardData();
    // Refresh data every 5 minutes
    setInterval(fetchDashboardData, 300000);
});

// Initialize time frame buttons
function initializeTimeframeButtons() {
    const buttons = document.querySelectorAll('[data-timeframe]');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            buttons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            currentTimeframe = this.getAttribute('data-timeframe');
            
            // Show/hide custom date range
            if (currentTimeframe === 'custom') {
                document.getElementById('customDateRange').classList.remove('d-none');
            } else {
                document.getElementById('customDateRange').classList.add('d-none');
                fetchDashboardData();
            }
        });
    });
    
    // Custom date range apply button
    document.getElementById('applyCustomRange').addEventListener('click', function() {
        customStartDate = document.getElementById('startDate').value;
        customEndDate = document.getElementById('endDate').value;
        
        if (customStartDate && customEndDate) {
            // Use the enhanced custom timeframe function
            fetchCustomTimeframeData();
        } else {
            alert('Please select both start and end dates');
        }
    });
}

// Fetch dashboard data from API
async function fetchDashboardData() {
    try {
        // Show loading overlay for dashboard content
        showLoading();
        
        // Build URL with timeframe parameters
        let url = '/api/dashboard-data?timeframe=' + currentTimeframe;
        
        if (currentTimeframe === 'custom' && customStartDate && customEndDate) {
            url += `&start_date=${customStartDate}&end_date=${customEndDate}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        updateMetrics(data.metrics, data.timeframe_label);
        updateCharts(data.chart_data);
        
        // Hide loading overlay for dashboard
        hideLoading();
        
        // Load activity table separately (has its own loading state)
        updateActivityTable();
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        hideLoading();
    }
}

// Fetch custom timeframe data with enhanced loading
async function fetchCustomTimeframeData() {
    try {
        // Show enhanced loading message for custom timeframe
        showCustomTimeframeLoading();
        
        const url = `/api/custom-timeframe-data?start_date=${customStartDate}&end_date=${customEndDate}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            updateMetrics(data.metrics, data.timeframe_label);
            updateCharts(data.chart_data);
        } else {
            console.error('Custom timeframe error:', data.error);
            showCustomTimeframeError(data.error);
        }
        
        // Hide loading overlay
        hideCustomTimeframeLoading();
        
        // Load activity table separately
        updateActivityTable();
        
    } catch (error) {
        console.error('Error fetching custom timeframe data:', error);
        hideCustomTimeframeLoading();
        showCustomTimeframeError('Failed to fetch data. Please try again.');
    }
}

// Show loading overlay
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('show');
    }
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
}

// Show custom timeframe loading with enhanced message
function showCustomTimeframeLoading() {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = overlay.querySelector('.loading-text');
    const customMessage = document.getElementById('customRangeMessage');
    
    if (overlay) {
        if (loadingText) {
            loadingText.textContent = 'This action needs more time - fetching data...';
        }
        overlay.classList.add('show');
    }
    
    if (customMessage) {
        customMessage.textContent = 'Fetching data - this may take a moment...';
        customMessage.className = 'text-warning';
    }
}

// Hide custom timeframe loading
function hideCustomTimeframeLoading() {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = overlay.querySelector('.loading-text');
    const customMessage = document.getElementById('customRangeMessage');
    
    if (overlay) {
        if (loadingText) {
            loadingText.textContent = 'Loading data...';
        }
        overlay.classList.remove('show');
    }
    
    if (customMessage) {
        customMessage.textContent = 'Custom timeframes may take longer to process';
        customMessage.className = 'text-muted';
    }
}

// Show custom timeframe error
function showCustomTimeframeError(errorMessage) {
    // You could implement a toast notification or alert here
    console.error('Custom timeframe error:', errorMessage);
    alert(`Error: ${errorMessage}`);
}

// Update metric cards
function updateMetrics(metrics, timeframeLabel) {
    // Number of Leads (Interested)
    document.getElementById('total-leads').textContent = metrics.total_leads.toLocaleString();
    
    // Reply Rate
    document.getElementById('reply-rate').textContent = metrics.reply_rate.toFixed(1);
    document.getElementById('reply-count').textContent = metrics.reply_count.toLocaleString();
    
    // Positive Rate
    document.getElementById('positive-rate').textContent = metrics.positive_rate.toFixed(1);
    
    // Prospects Contacted
    document.getElementById('prospects-contacted').textContent = metrics.prospects_contacted.toLocaleString();
    document.getElementById('emails-sent').textContent = metrics.emails_sent.toLocaleString();
    
    // Update Pipeline Calculator
    updatePipelineCalculator(metrics.total_leads);
}

// Update all charts
function updateCharts(chartData) {
    updateRepliesTimeChart(chartData.replies_over_time);
    updateCampaignBreakdownChart(chartData.campaign_breakdown);
    updateReplyStatusChart(chartData.reply_status);
    updateCampaignPerformanceChart(chartData.campaign_performance);
    updateInteractiveMap(chartData.map_locations);
}

// Chart instances
let repliesTimeChart = null;
let campaignBreakdownChart = null;
let replyStatusChart = null;
let campaignPerformanceChart = null;

// 1. Replies Over Time Chart
function updateRepliesTimeChart(data) {
    const ctx = document.getElementById('repliesTimeChart').getContext('2d');
    
    if (repliesTimeChart) {
        repliesTimeChart.destroy();
    }
    
    repliesTimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'All Replies',
                    data: data.all_values,
                    borderColor: '#ff6b35',
                    backgroundColor: 'rgba(255, 107, 53, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#ff6b35',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                },
                {
                    label: 'Interested Leads',
                    data: data.positive_values,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// 2. Campaign Breakdown Pie Chart
function updateCampaignBreakdownChart(data) {
    const ctx = document.getElementById('campaignBreakdownChart').getContext('2d');
    
    if (campaignBreakdownChart) {
        campaignBreakdownChart.destroy();
    }
    
    campaignBreakdownChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    'rgba(255, 107, 53, 0.8)',
                    'rgba(139, 69, 19, 0.8)',
                    'rgba(220, 38, 38, 0.8)',
                    'rgba(108, 117, 125, 0.8)',
                    'rgba(139, 0, 0, 0.8)',
                    'rgba(0, 0, 0, 0.6)'
                ],
                borderColor: '#fff',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 3. Reply Status Breakdown Chart
function updateReplyStatusChart(data) {
    const ctx = document.getElementById('replyStatusChart').getContext('2d');
    
    if (replyStatusChart) {
        replyStatusChart.destroy();
    }
    
    replyStatusChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(108, 117, 125, 0.8)'
                ],
                borderColor: '#fff',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 4. Campaign Performance Chart - Positive Rate (Positive Replies / Contacted)
function updateCampaignPerformanceChart(data) {
    const ctx = document.getElementById('campaignPerformanceChart').getContext('2d');
    
    if (campaignPerformanceChart) {
        campaignPerformanceChart.destroy();
    }
    
    campaignPerformanceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Positive Rate (%)',
                    data: data.rates,
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(255, 107, 53, 0.8)',
                        'rgba(139, 69, 19, 0.8)',
                        'rgba(220, 38, 38, 0.8)',
                        'rgba(108, 117, 125, 0.8)',
                        'rgba(139, 0, 0, 0.8)',
                        'rgba(34, 197, 94, 0.8)',
                        'rgba(249, 115, 22, 0.8)',
                        'rgba(168, 85, 247, 0.8)',
                        'rgba(236, 72, 153, 0.8)'
                    ],
                    borderColor: '#fff',
                    borderWidth: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 11
                        },
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map((label, i) => {
                                    const value = data.datasets[0].data[i];
                                    return {
                                        text: `${label}: ${value}%`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const rate = context.parsed;
                            const positive = data.positive_counts[context.dataIndex];
                            const contacted = data.contacted_counts[context.dataIndex];
                            return [
                                `${context.label}`,
                                `Positive Rate: ${rate}%`,
                                `Positive Replies: ${positive}`,
                                `Contacted: ${contacted}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

// 6. Interactive Choropleth Map (US States)
let leadsMap = null;
let stateLayer = null;

function updateInteractiveMap(stateData) {
    // Check if map container exists
    const mapContainer = document.getElementById('leadsLocationMap');
    if (!mapContainer) {
        console.error('Map container not found');
        return;
    }
    
    // Initialize map if not already created
    if (!leadsMap) {
        try {
            leadsMap = L.map('leadsLocationMap').setView([39.8283, -98.5795], 4);
            
            // Add tile layer (OpenStreetMap)
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18,
                minZoom: 3
            }).addTo(leadsMap);
        } catch (error) {
            console.error('Error initializing map:', error);
            return;
        }
    }
    
    // Clear existing state layer
    if (stateLayer) {
        leadsMap.removeLayer(stateLayer);
    }
    
    // Create state data lookup and find max replies for color scaling
    const stateDataMap = {};
    let maxReplies = 0;
    stateData.forEach(state => {
        stateDataMap[state.state_name] = state;
        maxReplies = Math.max(maxReplies, state.total_replies);
    });
    
    // Get color based on reply count
    function getColor(replies) {
        if (!replies || replies === 0) return '#e5e7eb';
        const intensity = replies / maxReplies;
        
        // Blue gradient from light to dark
        if (intensity > 0.8) return '#1e3a8a';
        if (intensity > 0.6) return '#2563eb';
        if (intensity > 0.4) return '#3b82f6';
        if (intensity > 0.2) return '#60a5fa';
        return '#93c5fd';
    }
    
    // Style each state
    function style(feature) {
        const stateName = feature.properties.name;
        const stateInfo = stateDataMap[stateName];
        const replies = stateInfo ? stateInfo.total_replies : 0;
        
        return {
            fillColor: getColor(replies),
            weight: 2,
            opacity: 1,
            color: '#ffffff',
            fillOpacity: 0.7
        };
    }
    
    // Highlight feature on hover
    function highlightFeature(e) {
        const layer = e.target;
        const stateName = layer.feature.properties.name;
        const stateInfo = stateDataMap[stateName];
        
        layer.setStyle({
            weight: 3,
            color: '#1f2937',
            fillOpacity: 0.9
        });
        
        layer.bringToFront();
        
        // Show tooltip with data
        if (stateInfo) {
            layer.bindTooltip(`
                <div style="font-size: 13px; padding: 5px;">
                    <strong>${stateName}</strong><br/>
                    <span style="color: #3b82f6;">Replied: ${stateInfo.replied}</span><br/>
                    <span style="color: #10b981;">Interested: ${stateInfo.interested}</span>
                </div>
            `, {
                permanent: false,
                direction: 'top',
                className: 'state-tooltip'
            }).openTooltip();
        } else {
            layer.bindTooltip(`
                <div style="font-size: 13px; padding: 5px;">
                    <strong>${stateName}</strong><br/>
                    No activity
                </div>
            `, {
                permanent: false,
                direction: 'top',
                className: 'state-tooltip'
            }).openTooltip();
        }
    }
    
    // Reset highlight on mouse out
    function resetHighlight(e) {
        stateLayer.resetStyle(e.target);
        e.target.closeTooltip();
    }
    
    // Zoom to state on click
    function zoomToFeature(e) {
        leadsMap.fitBounds(e.target.getBounds());
    }
    
    // Attach events to each feature
    function onEachFeature(feature, layer) {
        layer.on({
            mouseover: highlightFeature,
            mouseout: resetHighlight,
            click: zoomToFeature
        });
    }
    
    // Load US states GeoJSON and create choropleth
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            stateLayer = L.geoJson(data, {
                style: style,
                onEachFeature: onEachFeature
            }).addTo(leadsMap);
            
            console.log(`Choropleth map updated with ${stateData.length} states with activity`);
        })
        .catch(error => {
            console.error('Error loading GeoJSON:', error);
        });
}

// Recent Activity - Replies Data
let activityData = null;
let currentActivityTab = 'all';

// Update activity table with real data
async function updateActivityTable() {
    const tableBody = document.getElementById('activity-table');
    
    try {
        // Show loading state
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Loading replies...</td></tr>';
        
        const response = await fetch('/api/recent-activity');
        activityData = await response.json();
        
        if (activityData.success) {
            // Render current tab
            renderActivityTable(currentActivityTab);
        } else {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No recent replies</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching activity:', error);
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading activity</td></tr>';
    }
}

// Render activity table based on current tab
function renderActivityTable(tab) {
    const tableBody = document.getElementById('activity-table');
    
    if (!activityData) {
        return;
    }
    
    const replies = tab === 'positive' ? activityData.positive_replies : activityData.all_replies;
    
    tableBody.innerHTML = '';
    
    if (replies.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No replies found</td></tr>';
        return;
    }
    
    replies.forEach(reply => {
        const statusClass = reply.interested ? 'status-interested' : 'status-replied';
        const statusText = reply.interested ? 'Interested' : 'Replied';
        
        // Format date with time
        const dateObj = new Date(reply.date_received);
        const formattedDateTime = dateObj.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        
        // Generate inbox URL using the reply UUID
        const replyUuid = reply.reply_uuid || '';
        const leadId = reply.lead_id || '';
        
        let inboxUrl = '';
        if (replyUuid && replyUuid.trim() !== '') {
            // Use the proper UUID from database (stored from API 'uuid' field)
            inboxUrl = `https://send.longrun.agency/inbox?reply_uuid=${replyUuid}`;
        } else if (leadId) {
            // Fallback: use lead_id
            inboxUrl = `https://send.longrun.agency/inbox?lead_id=${leadId}`;
        } else {
            // Final fallback: general inbox
            inboxUrl = `https://send.longrun.agency/inbox`;
        }
        
        const row = `
            <tr>
                <td><strong>${reply.lead_name || 'Unknown'}</strong></td>
                <td>${reply.lead_email}</td>
                <td>${reply.campaign_name}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${formattedDateTime}</td>
                <td class="text-center">
                    <a href="${inboxUrl}" target="_blank" class="btn btn-sm btn-outline-primary" title="View in EmailBison">
                        <i class="fas fa-eye"></i>
                    </a>
                </td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

// Activity Tab Switchers
document.getElementById('activity-all-tab').addEventListener('click', function() {
    currentActivityTab = 'all';
    document.getElementById('activity-all-tab').classList.add('active');
    document.getElementById('activity-positive-tab').classList.remove('active');
    renderActivityTable('all');
});

document.getElementById('activity-positive-tab').addEventListener('click', function() {
    currentActivityTab = 'positive';
    document.getElementById('activity-positive-tab').classList.add('active');
    document.getElementById('activity-all-tab').classList.remove('active');
    renderActivityTable('positive');
});

// Helper function to get icon for source
function getSourceIcon(source) {
    const icons = {
        'LinkedIn': 'linkedin',
        'Email Campaign': 'envelope',
        'Website Form': 'globe',
        'Referral': 'user-friends',
        'Cold Outreach': 'phone'
    };
    return icons[source] || 'circle';
}

// Helper function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
        return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

// Pipeline Calculator Functions
function updatePipelineCalculator(leadsCount) {
    // Update leads count
    document.getElementById('pipeline-leads').textContent = leadsCount.toLocaleString();
    
    // Calculate and update total
    calculatePipelineTotal();
}

function calculatePipelineTotal() {
    const leadsElement = document.getElementById('pipeline-leads');
    const avgDealValueElement = document.getElementById('avg-deal-value');
    const totalElement = document.getElementById('pipeline-total');
    
    // Get values
    const leads = parseInt(leadsElement.textContent.replace(/,/g, '')) || 0;
    const avgDealValue = parseFloat(avgDealValueElement.value) || 0;
    
    // Calculate total
    const total = leads * avgDealValue;
    
    // Format and display
    totalElement.textContent = '$' + total.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

// Initialize pipeline calculator on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add event listener to average deal value input
    const avgDealValueInput = document.getElementById('avg-deal-value');
    if (avgDealValueInput) {
        avgDealValueInput.addEventListener('input', calculatePipelineTotal);
        avgDealValueInput.addEventListener('change', calculatePipelineTotal);
        
        // Initial calculation
        calculatePipelineTotal();
    }
});

