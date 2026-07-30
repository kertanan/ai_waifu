const apiToken = process.env.LM_API_TOKEN;
const response = await fetch('http://localhost:1234/api/v0/models', {
  headers: {
	'Authorization': `Bearer ${apiToken}`
  }
});
const models = await response.json();
console.log(models);
