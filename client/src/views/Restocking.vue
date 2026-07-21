<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <form class="budget-form" @submit.prevent="submitBudget">
        <div class="form-group">
          <label for="restocking-budget">{{ t('restocking.budgetLabel') }}</label>
          <input
            id="restocking-budget"
            v-model.number="budget"
            type="number"
            min="0"
            step="0.01"
            :placeholder="t('restocking.budgetPlaceholder')"
            class="budget-input"
          />
        </div>
        <div class="form-group-btn">
          <button type="submit" class="btn-primary" :disabled="!budget || budget <= 0">
            {{ t('restocking.submit') }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="hasSearched">
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.budget') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ summary.budget.toFixed(2) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.summary.totalAllocated') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ summary.total_allocated.toFixed(2) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.remainingBudget') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ summary.remaining_budget.toFixed(2) }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.itemsRecommended') }}</div>
          <div class="stat-value">{{ summary.items_recommended }}</div>
        </div>
      </div>

      <div v-if="recommendations.length === 0" class="empty-state">
        {{ t('restocking.emptyState') }}
      </div>
      <div v-else class="card">
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th>{{ t('restocking.table.onHand') }}</th>
                <th>{{ t('restocking.table.reorderPoint') }}</th>
                <th>{{ t('restocking.table.demand') }}</th>
                <th>{{ t('restocking.table.recommendedQty') }}</th>
                <th>{{ t('restocking.table.allocatedQty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ translateWarehouse(item.warehouse) }}</td>
                <td>{{ item.quantity_on_hand }}</td>
                <td>{{ item.reorder_point }}</td>
                <td>{{ item.demand_score }}</td>
                <td>{{ item.recommended_quantity }}</td>
                <td>
                  <span :class="['badge', item.allocated_quantity < item.recommended_quantity ? 'warning' : 'success']">
                    {{ item.allocated_quantity }}
                  </span>
                </td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>{{ currencySymbol }}{{ item.line_cost.toFixed(2) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName, translateWarehouse } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const budget = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const hasSearched = ref(false)

    const summary = ref({
      budget: 0,
      total_allocated: 0,
      remaining_budget: 0,
      items_recommended: 0
    })
    const recommendations = ref([])

    const loadRecommendations = async () => {
      if (!(budget.value > 0)) return

      loading.value = true
      error.value = null
      try {
        const data = await api.getRestockingRecommendations(budget.value, getCurrentFilters())
        summary.value = data.summary
        recommendations.value = data.recommendations
      } catch (err) {
        error.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => {
      if (hasSearched.value) loadRecommendations()
    })

    const submitBudget = () => {
      hasSearched.value = true
      loadRecommendations()
    }

    return {
      t,
      budget,
      loading,
      error,
      hasSearched,
      summary,
      recommendations,
      submitBudget,
      currencySymbol,
      translateProductName,
      translateWarehouse
    }
  }
}
</script>

<style scoped>
.budget-form {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
}

.budget-input {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
  transition: border-color 0.2s ease;
  min-width: 220px;
}

.budget-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.form-group-btn {
  display: flex;
  align-items: flex-end;
}

.btn-primary {
  padding: 0.75rem 1.75rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
  white-space: nowrap;
  height: fit-content;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  padding: 3rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}
</style>
