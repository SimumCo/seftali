import api from './api';

export const gibApi = {
  connect: (data) => api.post('/gib/live/connect', data),
  status: () => api.get('/gib/live/status'),
  startImport: (data) => api.post('/gib/live/import/start', data),
  disconnect: () => api.post('/gib/live/disconnect'),
  createOutboxInvoice: (payload) => api.post('/gib/live/outbox/create', payload),
};

export default gibApi;
