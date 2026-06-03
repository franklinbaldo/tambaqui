document.addEventListener('DOMContentLoaded', () => {
      const entries = [];
      const updateFromInput = document.getElementById('updateFromInput');
      const updateToInput = document.getElementById('updateToInput');
      const descriptionInput = document.getElementById('descriptionInput');
      const amountInput = document.getElementById('amountInput');
      const addEntryButton = document.getElementById('addEntryButton');
      const entriesTableBody = document.getElementById('entriesTableBody');
      const totalAmountDisplay = document.getElementById('totalAmount');
      const totalUpdatedAmountDisplay = document.getElementById('totalUpdatedAmount');
      const errorMessage = document.getElementById('errorMessage');
      const emptyState = document.getElementById('emptyState');

      addEntryButton.addEventListener('click', async () => {
        // Clear previous error messages and hide error display
        errorMessage.classList.add('is-hidden');
        errorMessage.textContent = ''; // Clear previous message content

        // Add loading state to button
        addEntryButton.classList.add('is-loading');

        try {
          const updateFrom = updateFromInput.value;
          const updateTo = updateToInput.value;
          const description = descriptionInput.value;
          const amount = parseFloat(amountInput.value);

          // Specific input validation
          if (!updateFrom) {
            errorMessage.textContent = "Please enter a valid 'Update From' date.";
            throw new Error('Input validation failed');
          }
          if (!updateTo) {
            errorMessage.textContent = "Please enter a valid 'Update To' date.";
            throw new Error('Input validation failed');
          }
          if (!description) {
            errorMessage.textContent = "Please enter a description.";
            throw new Error('Input validation failed');
          }
          if (isNaN(amount) || amount <= 0) {
            errorMessage.textContent = "Please enter a valid positive amount.";
            throw new Error('Input validation failed');
          }

          // If validation passes, ensure error message is hidden before fetching
          errorMessage.classList.add('is-hidden');

          const factorFrom = await fetchFactor(updateFrom);
          const factorTo = await fetchFactor(updateTo);
          const updatedAmount = (amount * factorFrom) / factorTo;

          entries.push({ updateFrom, description, amount, updatedAmount });
          updateTable();

          descriptionInput.value = '';
          amountInput.value = '';
        } catch (error) {
          // If errorMessage.textContent is already set by validation, it will be displayed
          // Otherwise, set a generic message or use error.message if available
          if (!errorMessage.textContent) {
            errorMessage.textContent = error.message || 'An unexpected error occurred.';
          }
          errorMessage.classList.remove('is-hidden');
        } finally {
          // Remove loading state from button
          addEntryButton.classList.remove('is-loading');
        }
      });

      function deleteEntry(index) {
        entries.splice(index, 1);
        updateTable();
      }

      async function fetchFactor(date) {
        // Extract YYYY-MM from the input date string
        const yearMonth = date.substring(0, 7); // Extracts "YYYY-MM"

        try {
          const response = await fetch('tabela_de_atualizacao_ec113.json');
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const data = await response.json();

          if (data[yearMonth] && data[yearMonth].Fator) {
            return parseFloat(data[yearMonth].Fator);
          } else {
            // More specific error message for factor not found
            throw new Error(`Factor not found for ${yearMonth}.`);
          }
        } catch (error) {
          console.error('Error fetching or parsing factor data:', error);
          // Check if it's the specific "Factor not found" error to customize message
          if (error.message.startsWith('Factor not found for')) {
             errorMessage.textContent = error.message; // Use the specific message from fetchFactor
          }
          throw error; // Re-throw the error to be caught by the caller
        }
      }

      function updateTable() {
        let totalAmount = 0;
        let totalUpdatedAmount = 0;
        entriesTableBody.innerHTML = entries.map((entry, index) => {
          totalAmount += entry.amount;
          totalUpdatedAmount += entry.updatedAmount;
          return `
            <tr>
              <td>${entry.updateFrom}</td>
              <td>${entry.description}</td>
              <td>${entry.amount.toFixed(2)}</td>
              <td>${entry.updatedAmount.toFixed(2)}</td>
              <td>
                <button class="button is-danger" onclick="deleteEntry(${index})">Delete</button>
              </td>
            </tr>
          `;
        }).join('') + `
          <tr>
            <td colspan="2"><strong>Total</strong></td>
            <td><strong>${totalAmount.toFixed(2)}</strong></td>
            <td><strong>${totalUpdatedAmount.toFixed(2)}</strong></td>
            <td></td>
          </tr>
        `;
        totalAmountDisplay.textContent = totalAmount.toFixed(2);
        totalUpdatedAmountDisplay.textContent = totalUpdatedAmount.toFixed(2);
        emptyState.style.display = entries.length > 0 ? 'none' : 'table-row';
      }

      window.deleteEntry = deleteEntry;

      async function renderChart() {
        try {
          const response = await fetch('tabela_de_atualizacao_ec113.json');
          if (!response.ok) {
            throw new Error(`Chart data HTTP error! status: ${response.status}`);
          }
          const allFactorData = await response.json();

          const labels = Object.keys(allFactorData).sort(); // Sort YYYY-MM keys chronologically
          const dataPoints = labels.map(label => allFactorData[label].Fator);

          const ctx = document.getElementById('factorTrendChart').getContext('2d');
          if (!ctx) {
            console.error('Could not find canvas element for chart.');
            return;
          }

          new Chart(ctx, {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{
                label: 'Fator de Atualização Monetária',
                data: dataPoints,
                borderColor: 'hsl(217, 71%, 53%)', // Bulma primary color
                backgroundColor: 'hsla(217, 71%, 53%, 0.1)', // Optional: for area fill
                tension: 0.1,
                fill: true
              }]
            },
            options: {
              scales: {
                y: {
                  beginAtZero: false,
                  ticks: {
                    callback: function(value, index, values) {
                      return value.toFixed(4); // Format y-axis ticks if needed
                    }
                  }
                },
                x: {
                   title: {
                        display: true,
                        text: 'Ano-Mês'
                    }
                }
              },
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(6); // More precision on tooltip
                            }
                            return label;
                        }
                    }
                }
              }
            }
          });
        } catch (error) {
          console.error('Error rendering chart:', error);
          const chartCanvas = document.getElementById('factorTrendChart');
          if (chartCanvas) {
            const ctx = chartCanvas.getContext('2d');
            ctx.font = "16px Arial";
            ctx.fillStyle = "red";
            ctx.textAlign = "center";
            ctx.fillText("Error loading chart data.", chartCanvas.width/2, chartCanvas.height/2);
          }
        }
      }

      renderChart(); // Call the function to render the chart on DOMContentLoaded
    });
