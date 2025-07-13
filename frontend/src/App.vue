<template>
  <div id="app">
    <div class="grid-container">

      <aside class="sidebar">
        <h1 class="app-title">RiskConcile<br>Stock Tracker</h1>

        <div class="search-section panel">
          <h2>SEARCH TERMINAL</h2>
          <input
            v-model="tickerInput"
            @keyup.enter="searchStock"
            placeholder="Enter ticker (e.g., TSLA)"
            class="ticker-input"
          />
          <button @click="searchStock" class="search-button">SEARCH</button>
          <div v-if="loading" class="message loading">Processing data feed...</div>
          <div v-if="error" class="message error">{{ error }}</div>
        </div>

        <div class="watchlist-section panel">
          <h2>WATCHLIST</h2>
          <div v-if="watchlist.length === 0" class="message">No assets monitored.</div>
          <div v-else class="watchlist-grid">
            <div
              v-for="ticker in watchlist"
              :key="ticker"
              @click="selectWatchlistStock(ticker)"
              class="watchlist-item"
            >
              <span>{{ ticker }}</span>
              <button @click.stop="toggleWatchlist(ticker)" class="remove-button">[X]</button>
            </div>
          </div>
        </div>
      </aside> <main class="main-content">
        <section class="stock-chart-area panel">
          <div v-if="currentStock" class="stock-details-and-chart">
            <div class="stock-details">
                <h2 class="stock-name">{{ currentStock.name || currentStock.symbol }}</h2>
                <div class="price-info">
                    <p class="price">{{ formatCurrency(currentStock.price) }}</p>
                    <p :class="['change', { 'positive': currentStock.change > 0, 'negative': currentStock.change < 0 }]">
                      {{ formatCurrency(currentStock.change) }} ({{ currentStock.change_percent }})
                    </p>
                </div>
                <button
                  @click="toggleWatchlist(currentStock.symbol)"
                  :class="['watchlist-button', { 'added': isInWatchlist(currentStock.symbol) }]"
                >
                  {{ isInWatchlist(currentStock.symbol) ? 'REMOVE FROM GRID' : 'ADD TO GRID' }}
                </button>
            </div>

            <div v-if="chartData.labels.length > 0" class="chart-container">
              <h3>HISTORICAL DATA [LAST 30 CYCLES]</h3>
              <Line
                :data="chartData"
                :options="{ responsive: true, maintainAspectRatio: false, scales: chartScales, plugins: chartPlugins }"
              />
            </div>
            <div v-else class="message">No historical data available for {{ currentStock.symbol }}.</div>
          </div>
          <div v-else class="message no-stock-selected">
              <p>Initiate scan to view asset data.</p>
              <p>Status: Awaiting Input</p>
          </div>
        </section>

        <section class="empty-area panel">
          <h2>LOGS / SYSTEM MESSAGES</h2>
          <p>System operational. Awaiting further commands.</p>
          <p>[07-13-2025 18:45:00] Data stream established.</p>
        </section>
      </main>
    </div> </div> </template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import axios from 'axios';

// --- Chart.js Imports & Registration ---
import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
} from 'chart.js';

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement
);

// --- State Variables ---
const tickerInput = ref('');
const currentStock = ref(null);
const watchlist = ref([]);
const loading = ref(false);
const error = ref(null);

// --- Configuration ---
const BACKEND_URL = import.meta.env.VITE_APP_BACKEND_URL || 'http://localhost:8000';

// --- Chart Data Computed Property ---
const chartData = computed(() => {
  if (!currentStock.value || !currentStock.value.historical_data || currentStock.value.historical_data.length === 0) {
    return {
      labels: [],
      datasets: []
    };
  }

  const sortedData = [...currentStock.value.historical_data].sort((a, b) => new Date(a.date) - new Date(b.date));

  const labels = sortedData.map(data => data.date);
  const prices = sortedData.map(data => data.close);

  return {
    labels: labels,
    datasets: [
      {
        label: `${currentStock.value.symbol} Price`,
        backgroundColor: '#00FFFF', // Neon Cyan
        borderColor: '#00FFFF',
        data: prices,
        fill: false,
        tension: 0.2, // Slightly more curve for sleekness
        pointRadius: 3,
        pointBackgroundColor: '#00FFFF',
        pointBorderColor: '#00FFFF',
      },
    ],
  };
});

// --- Chart Scales and Plugins for Cyberpunk Look ---
const chartScales = {
  x: {
    ticks: { color: '#00FF00', font: { family: 'Share Tech Mono' } }, // Neon Green for X-axis labels
    grid: { color: 'rgba(0, 255, 0, 0.1)' }, // Subtle green grid
    title: { display: true, text: 'Date', color: '#00FF00', font: { family: 'Share Tech Mono' } }
  },
  y: {
    ticks: { color: '#FF00FF', font: { family: 'Share Tech Mono' } }, // Neon Magenta for Y-axis labels
    grid: { color: 'rgba(255, 0, 255, 0.1)' }, // Subtle magenta grid
    title: { display: true, text: 'Price (USD)', color: '#FF00FF', font: { family: 'Share Tech Mono' } }
  }
};

const chartPlugins = {
  legend: {
    labels: {
      color: '#00FFFF', // Neon Cyan for legend labels
      font: { family: 'Rajdhani' }
    }
  },
  tooltip: {
    backgroundColor: 'rgba(20, 20, 20, 0.8)',
    borderColor: '#00FFFF',
    borderWidth: 1,
    titleColor: '#00FFFF',
    bodyColor: '#FFFFFF',
    font: { family: 'Share Tech Mono' }
  }
};

// --- Methods ---
const searchStock = async () => {
  if (!tickerInput.value) {
    error.value = 'Please enter a stock ticker.';
    currentStock.value = null;
    return;
  }
  loading.value = true;
  error.value = null;
  currentStock.value = null;

  try {
    const response = await axios.get(`${BACKEND_URL}/api/stock/${tickerInput.value.toUpperCase()}`);
    currentStock.value = response.data;
  } catch (err) {
    if (err.response) {
      if (err.response.status === 404) {
        error.value = `Asset "${tickerInput.value.toUpperCase()}" not found in database.`;
      } else if (err.response.status === 429) {
        error.value = `API call limit exceeded. Initiate cooldown protocol.`;
      } else {
        error.value = `Backend error (${err.response.status}): ${err.response.data.detail || err.message}.`;
      }
    } else {
      error.value = `Network error: ${err.message}. Verify backend matrix connection.`;
    }
    console.error('Error fetching stock:', err);
  } finally {
    loading.value = false;
  }
};

// New method to select stock from watchlist
const selectWatchlistStock = (ticker) => {
  tickerInput.value = ticker;
  searchStock();
};

const loadWatchlist = () => {
  const storedWatchlist = localStorage.getItem('stock_watchlist');
  if (storedWatchlist) {
    watchlist.value = JSON.parse(storedWatchlist);
  }
};

const saveWatchlist = () => {
  localStorage.setItem('stock_watchlist', JSON.stringify(watchlist.value));
};

const isInWatchlist = (ticker) => {
  return watchlist.value.includes(ticker);
};

const toggleWatchlist = (ticker) => {
  if (isInWatchlist(ticker)) {
    watchlist.value = watchlist.value.filter(t => t !== ticker);
  } else {
    watchlist.value.push(ticker);
  }
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '';
  const numValue = parseFloat(value);
  if (isNaN(numValue)) return value;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numValue);
};


// --- Lifecycle Hooks ---
onMounted(() => {
  loadWatchlist();
});

watch(watchlist, saveWatchlist, { deep: true });
</script>

<style>
/* --- Google Fonts for Cyberpunk Theme --- */
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');

/* Global styles and reset */
body {
  margin: 0;
  font-family: 'Rajdhani', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #0d0d0d; /* Deep dark background */
  color: #e0e0e0; /* Light gray for general text */
  overflow: hidden; /* Prevent body scroll if grid container has its own scroll */
}

#app {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  box-sizing: border-box;
}

.grid-container {
  display: grid;
  grid-template-columns: 1fr 3fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  width: 100%;
  max-width: 1200px;
  height: 90vh;
  min-height: 600px;
  background-color: #1a1a1a; /* Slightly lighter dark background for the main container */
  border: 1px solid #00FFFF; /* Neon Cyan border */
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.4), inset 0 0 5px rgba(0, 255, 255, 0.2); /* Inner and outer glow */
  border-radius: 4px; /* Slightly sharp corners */
  overflow: hidden;
}

/* Assign grid areas */
.sidebar {
  grid-column: 1;
  grid-row: 1 / span 2;
  background-color: #1a1a1a;
  color: #e0e0e0;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  border-right: 1px solid #00FFFF; /* Separator line */
}

.main-content {
  grid-column: 2;
  grid-row: 1 / span 2;
  display: grid;
  grid-template-rows: auto 1fr; /* Chart area auto, empty area fills rest */
  gap: 20px;
  padding: 20px;
  overflow-y: auto;
}

.stock-chart-area {
  background-color: #222222; /* Darker panel for chart area */
  display: flex;
  flex-direction: column;
  padding: 15px;
  border: 1px solid #FF00FF; /* Neon Magenta border */
  border-radius: 4px;
  box-shadow: 0 0 10px rgba(255, 0, 255, 0.3);
}

.empty-area {
  background-color: #222222; /* Darker panel for empty area */
  padding: 15px;
  border: 1px solid #00FF00; /* Neon Green border */
  border-radius: 4px;
  box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
}

/* Base Panel Styling */
.panel {
    border: 1px solid #333; /* Subtle dark border for structure */
    border-radius: 4px;
}

/* Specific element styles */
h1, h2, h3 {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 600;
  text-transform: uppercase;
  color: #00FFFF; /* Neon Cyan for titles */
  letter-spacing: 1.5px;
  text-shadow: 0 0 8px rgba(0, 255, 255, 0.6); /* Glow effect */
}

.app-title {
    font-size: 2.5em;
    text-align: center;
    margin-bottom: 30px;
    line-height: 1.1;
}

.search-section h2, .watchlist-section h2, .stock-chart-area h2, .empty-area h2 {
    color: #00FFFF; /* Neon Cyan */
    text-shadow: 0 0 5px rgba(0, 255, 255, 0.4);
}
.main-content .stock-chart-area h2, .main-content .empty-area h2 {
    color: #00FF00; /* Neon Green for main content titles */
    text-shadow: 0 0 5px rgba(0, 255, 0, 0.4);
}

.ticker-input {
  width: calc(100% - 20px);
  margin-bottom: 10px;
  padding: 10px;
  border: 1px solid #00FFFF; /* Neon Cyan border */
  background-color: #0d0d0d; /* Dark input background */
  color: #00FF00; /* Neon Green input text */
  border-radius: 4px;
  box-sizing: border-box;
  font-family: 'Share Tech Mono', monospace; /* Monospaced font for input */
}
.ticker-input::placeholder {
  color: rgba(0, 255, 255, 0.5); /* Lighter placeholder */
}

.search-button {
  width: 100%;
  padding: 10px;
  background-color: #00FFFF; /* Neon Cyan button */
  color: #0d0d0d; /* Dark text */
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  font-family: 'Rajdhani', sans-serif;
  text-transform: uppercase;
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
  box-shadow: 0 0 8px rgba(0, 255, 255, 0.6);
}

.search-button:hover {
  background-color: #00e6e6; /* Slightly darker neon on hover */
  box-shadow: 0 0 12px rgba(0, 255, 255, 0.8);
}

.message {
  padding: 10px;
  margin-top: 10px;
  border-radius: 4px;
  font-size: 0.9em;
  background-color: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 255, 255, 0.2);
  color: #e0e0e0;
  font-family: 'Share Tech Mono', monospace;
}
.message.loading {
    color: #00FFFF;
    border-color: #00FFFF;
    box-shadow: 0 0 5px rgba(0, 255, 255, 0.4);
}

.message.error {
  background-color: #4d0000; /* Dark red */
  border-color: #FF0000; /* Bright red */
  color: #FF6666; /* Lighter red */
  box-shadow: 0 0 8px rgba(255, 0, 0, 0.6);
}
.message.no-stock-selected {
    background-color: #222222;
    border-color: #FF00FF;
    color: #FF00FF;
    text-align: center;
    box-shadow: 0 0 5px rgba(255, 0, 255, 0.4);
}

/* --- Stock Details Layout --- */
.stock-details-and-chart {
  display: flex;
  flex-direction: column;
}

.stock-details {
    display: flex; /* Make details horizontal */
    justify-content: space-between; /* Space out items */
    align-items: center; /* Vertically align items */
    padding-bottom: 15px;
    margin-bottom: 15px;
    border-bottom: 1px dotted #444; /* Dotted separator */
}
.stock-details .stock-name {
    font-size: 1.8em;
    margin: 0;
    color: #00FF00; /* Neon Green for stock name */
    text-shadow: 0 0 8px rgba(0, 255, 0, 0.6);
    flex-grow: 1; /* Allow name to take available space */
    text-align: left;
}
.stock-details .price-info {
    display: flex;
    align-items: baseline; /* Align price and change */
    gap: 15px; /* Space between price and change */
    margin: 0 20px;
}
.stock-details .price {
    font-size: 2.2em;
    font-weight: bold;
    color: #00FFFF; /* Neon Cyan for price */
    margin: 0;
}
.stock-details .change {
    font-size: 1.3em;
    font-weight: bold;
    margin: 0;
}
.stock-details .change.positive {
    color: #00FF00; /* Neon Green for positive */
    text-shadow: 0 0 5px rgba(0, 255, 0, 0.4);
}
.stock-details .change.negative {
    color: #FF0000; /* Bright Red for negative */
    text-shadow: 0 0 5px rgba(255, 0, 0, 0.4);
}

.watchlist-button {
  padding: 8px 15px;
  background-color: #5a125a; /* Darker purple */
  color: #FF00FF; /* Neon Magenta text */
  border: 1px solid #FF00FF;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  font-family: 'Rajdhani', sans-serif;
  text-transform: uppercase;
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
  box-shadow: 0 0 8px rgba(255, 0, 255, 0.6);
}

.watchlist-button:hover {
  background-color: #6d156d; /* Lighter purple on hover */
  box-shadow: 0 0 12px rgba(255, 0, 255, 0.8);
}

.watchlist-button.added {
  background-color: #800080; /* Brighter purple when added */
  color: #FFF;
  border-color: #FF00FF;
  box-shadow: 0 0 10px rgba(255, 0, 255, 0.8);
}
.watchlist-button.added:hover {
  background-color: #6a006a;
}


.watchlist-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-top: 10px;
}

.watchlist-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #00FFFF; /* Neon Cyan border */
  border-radius: 4px;
  background-color: rgba(0, 255, 255, 0.1); /* Subtle neon background */
  color: #e0e0e0;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease, box-shadow 0.2s ease;
  font-family: 'Share Tech Mono', monospace;
  box-shadow: 0 0 5px rgba(0, 255, 255, 0.2);
}

.watchlist-item:hover {
    background-color: rgba(0, 255, 255, 0.2);
    transform: translateY(-2px);
    box-shadow: 0 0 8px rgba(0, 255, 255, 0.6);
}

.watchlist-item span {
  font-weight: bold;
  color: #00FF00; /* Neon Green for ticker text */
}

.remove-button {
  background-color: #4d0000;
  color: #FF0000;
  border: 1px solid #FF0000;
  border-radius: 3px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 0.75em;
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
  font-family: 'Share Tech Mono', monospace;
  box-shadow: 0 0 5px rgba(255, 0, 0, 0.4);
}

.remove-button:hover {
  background-color: #660000;
  box-shadow: 0 0 8px rgba(255, 0, 0, 0.6);
}

/* --- CHART CONTAINER STYLING --- */
.chart-container {
  margin-top: 20px;
  height: 350px; /* FIXED HEIGHT for the chart */
  width: 100%;
  position: relative;
  overflow: hidden;
  background-color: #0d0d0d; /* Dark background for the chart area itself */
  border: 1px solid #FF00FF; /* Neon Magenta border */
  border-radius: 4px;
  box-shadow: 0 0 10px rgba(255, 0, 255, 0.4), inset 0 0 5px rgba(255, 0, 255, 0.2);
}
.chart-container h3 {
    color: #FF00FF; /* Neon Magenta for chart title */
    text-align: center;
    margin-bottom: 10px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .grid-container {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    height: auto;
    min-height: auto;
  }
  .sidebar {
    grid-column: 1;
    grid-row: 1;
    border-right: none; /* Remove right border */
    border-bottom: 1px solid #00FFFF; /* Add bottom border */
  }
  .main-content {
    grid-column: 1;
    grid-row: 2 / span 2;
    grid-template-rows: auto auto;
  }
  .app-title {
      font-size: 1.8em;
  }
  .stock-details {
      flex-direction: column; /* Stack details vertically on small screens */
      align-items: flex-start;
  }
  .stock-details .price-info {
      flex-direction: column;
      align-items: flex-start;
      margin: 10px 0;
      gap: 5px;
  }
  .stock-details .stock-name {
      text-align: center; /* Center name on small screens */
      width: 100%;
      margin-bottom: 10px;
  }
}
</style>