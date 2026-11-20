const apiToken = process.env.LM_API_TOKEN;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:1234';
const response = await fetch(`${API_BASE_URL}/api/v0/models`, {
  headers: {
	'Authorization': `Bearer ${apiToken}`
  }
});
const models = await response.json();
console.log(models);
