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
                    'rgba(0, 0, 0, 0.6)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 159, 64, 0.8)'
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
                                        text: `${label}: ${value}`,
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

// 6. Interactive Point Map (Individual Lead Locations)
let leadsMap = null;
let leadMarkers = null;

function updateInteractiveMap(leadLocations) {
    // Check if map container exists
    const mapContainer = document.getElementById('leadsLocationMap');
    if (!mapContainer) {
        console.error('Map container not found');
        return;
    }
    
    // Initialize map if not already created
    if (!leadsMap) {
        try {
            // Set initial view to center of US
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
    
    // Clear existing markers
    if (leadMarkers) {
        leadMarkers.clearLayers();
    } else {
        leadMarkers = L.layerGroup().addTo(leadsMap);
    }
    
    if (!leadLocations || leadLocations.length === 0) {
        console.log('No lead locations to display');
        return;
    }
    
    // Create markers for each lead location
    leadLocations.forEach(lead => {
        if (lead.lat && lead.lng) {
            // Create custom marker icon
            const markerIcon = L.divIcon({
                className: 'custom-marker',
                html: '<div class="marker-pin"></div>',
                iconSize: [20, 20],
                iconAnchor: [10, 20],
                popupAnchor: [0, -20]
            });
            
            // Create marker
            const marker = L.marker([lead.lat, lead.lng], { icon: markerIcon })
                .bindPopup(createLeadPopup(lead), {
                    maxWidth: 300,
                    className: 'lead-popup'
                });
            
            leadMarkers.addLayer(marker);
        }
    });
    
    // Fit map to show all markers
    if (leadLocations.length > 0) {
        const group = new L.featureGroup(leadMarkers.getLayers());
        leadsMap.fitBounds(group.getBounds().pad(0.1));
    }
    
    console.log(`Interactive map updated with ${leadLocations.length} lead locations`);
}

function createLeadPopup(lead) {
    const replyDate = new Date(lead.date_received).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
    
    return `
        <div class="lead-popup-content">
            <div class="lead-header">
                <h6 class="mb-1">${lead.name || 'Unknown Name'}</h6>
                <small class="text-muted">${lead.title || 'No Title'} at ${lead.company || 'Unknown Company'}</small>
            </div>
            <div class="lead-details mt-2">
                <div class="detail-row">
                    <i class="fas fa-envelope me-2"></i>
                    <span>${lead.email || 'No Email'}</span>
                </div>
                ${lead.phone ? `
                <div class="detail-row">
                    <i class="fas fa-phone me-2"></i>
                    <span>${lead.phone}</span>
                </div>
                ` : ''}
                <div class="detail-row">
                    <i class="fas fa-map-marker-alt me-2"></i>
                    <span>${lead.address || 'No Address'}</span>
                </div>
                <div class="detail-row">
                    <i class="fas fa-calendar me-2"></i>
                    <span>Replied: ${replyDate}</span>
                </div>
                ${lead.campaign_name ? `
                <div class="detail-row">
                    <i class="fas fa-bullhorn me-2"></i>
                    <span>Campaign: ${lead.campaign_name}</span>
                </div>
                ` : ''}
            </div>
        </div>
    `;
}

// Recent Activity - Replies Data
let activityData = null;
let currentActivityTab = 'all';

// Update activity table with real data
async function updateActivityTable() {
    const tableBody = document.getElementById('activity-table');
    
    try {
        // Show loading state
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Loading replies...</td></tr>';
        
        const response = await fetch('/api/recent-activity');
        activityData = await response.json();
        
        if (activityData.success) {
            // Render current tab
            renderActivityTable(currentActivityTab);
        } else {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No recent replies</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching activity:', error);
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading activity</td></tr>';
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
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No replies found</td></tr>';
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
                <td>${reply.lead_company || 'N/A'}</td>
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

