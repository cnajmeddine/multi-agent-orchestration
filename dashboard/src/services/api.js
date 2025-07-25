export const fetchData = async (endpoint) => {
  const res = await fetch(endpoint);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}; 