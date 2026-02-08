<template>
  <div class="container">
    <header class="header">
      <h1>Stack Docker + League of Legends</h1>
      <p class="subtitle">Vue.js → FastAPI → PostgreSQL + Riot API</p>
    </header>

    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'health' }" @click="activeTab = 'health'">Health</button>
      <button class="tab" :class="{ active: activeTab === 'champions' }" @click="activeTab = 'champions'">Champions</button>
    </div>

    <div v-show="activeTab === 'health'" class="card">
      <h2>État Backend</h2>
      <button @click="checkHealth" class="btn">Vérifier</button>
      <div v-if="health" class="status-box">{{ health.status }}</div>
    </div>

    <div v-show="activeTab === 'champions'" class="card">
      <h2>Champions LoL</h2>
      <div class="button-group">
        <button @click="syncChampions" class="btn btn-primary">Synchroniser</button>
        <button @click="fetchChampions" class="btn">Afficher</button>
      </div>
      <div v-if="syncMessage" class="info">{{ syncMessage }}</div>
      <div v-if="champions.length > 0">
        <p>{{ champions.length }} champions</p>
        <div class="champions-grid">
          <div v-for="champ in champions" :key="champ.id" class="champion-card" @click="openModal(champ.id)">
            <img v-if="champ.image_full" :src="imageBaseUrl + champ.image_full" :alt="champ.name" class="champ-img">
            <div class="champ-info">
              <h3>{{ champ.name }}</h3>
              <p>{{ champ.title }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal" @click="closeModal">
      <div class="modal-content" @click.stop>
        <button class="modal-close" @click="closeModal">×</button>
        <div v-if="selectedChampion" class="modal-body">
          <div class="modal-header">
            <img :src="imageBaseUrl + selectedChampion.image_full" class="modal-img">
            <div>
              <h2>{{ selectedChampion.name }}</h2>
              <p>{{ selectedChampion.title }}</p>
            </div>
          </div>
          <div v-if="selectedChampion.lore" class="lore">
            <h3>Histoire</h3>
            <p>{{ selectedChampion.lore }}</p>
          </div>
          <div v-if="selectedChampion.passive" class="passive">
            <h3>Passif: {{ selectedChampion.passive.name }}</h3>
            <p>{{ selectedChampion.passive.description }}</p>
          </div>
          <div v-if="selectedChampion.spells" class="spells">
            <h3>Compétences</h3>
            <div v-for="(spell, i) in selectedChampion.spells" :key="spell.id" class="spell">
              <strong>{{ ['Q', 'W', 'E', 'R'][i] }} - {{ spell.name }}</strong>
              <p>{{ spell.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      apiUrl: 'http://localhost:8000',
      activeTab: 'champions',
      health: null,
      champions: [],
      imageBaseUrl: '',
      syncMessage: '',
      showModal: false,
      selectedChampion: null
    }
  },
  methods: {
    async checkHealth() {
      const res = await fetch(this.apiUrl + '/health')
      this.health = await res.json()
    },
    async syncChampions() {
      const res = await fetch(this.apiUrl + '/api/champions/sync')
      const data = await res.json()
      this.syncMessage = data.message
      setTimeout(() => this.fetchChampions(), 500)
    },
    async fetchChampions() {
      const res = await fetch(this.apiUrl + '/api/champions')
      const data = await res.json()
      this.champions = data.champions || []
      this.imageBaseUrl = data.image_base_url || ''
    },
    async openModal(id) {
      this.showModal = true
      const res = await fetch(this.apiUrl + '/api/champions/' + id + '/details')
      const data = await res.json()
      this.selectedChampion = data.champion
    },
    closeModal() {
      this.showModal = false
      this.selectedChampion = null
    }
  },
  mounted() {
    this.checkHealth()
  }
}
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.header { text-align: center; color: white; margin-bottom: 30px; }
.header h1 { font-size: 2rem; margin: 0 0 10px 0; }
.tabs { display: flex; gap: 10px; margin-bottom: 20px; }
.tab { flex: 1; padding: 12px; background: white; border: none; border-radius: 8px 8px 0 0; cursor: pointer; }
.tab.active { background: #667eea; color: white; font-weight: bold; }
.card { background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; }
.card h2 { color: #667eea; margin: 0 0 15px 0; }
.button-group { display: flex; gap: 10px; margin-bottom: 15px; }
.btn { background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; margin: 5px; }
.btn-primary { background: #f5576c; }
.info { background: #d1ecf1; padding: 12px; border-radius: 8px; margin: 15px 0; }
.status-box { padding: 15px; background: #d4edda; border-radius: 8px; margin-top: 15px; }
.champions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; margin-top: 20px; }
.champion-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.3s; }
.champion-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(102,126,234,0.3); }
.champ-img { width: 100%; height: 180px; object-fit: cover; }
.champ-info { padding: 12px; }
.champ-info h3 { color: #667eea; margin: 0 0 5px 0; font-size: 1rem; }
.champ-info p { color: #764ba2; font-size: 0.85rem; margin: 0; }
.modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: white; border-radius: 16px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto; position: relative; }
.modal-close { position: absolute; top: 10px; right: 10px; background: #ff4444; color: white; border: none; width: 35px; height: 35px; border-radius: 50%; font-size: 20px; cursor: pointer; }
.modal-body { padding: 30px; }
.modal-header { display: flex; gap: 20px; margin-bottom: 20px; }
.modal-img { width: 120px; height: 120px; border-radius: 12px; }
.lore, .passive, .spells { margin-top: 20px; }
.lore h3, .passive h3, .spells h3 { color: #667eea; margin-bottom: 10px; }
.spell { background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
.spell strong { color: #667eea; display: block; margin-bottom: 5px; }
</style>
