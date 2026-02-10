import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import appConfig from './config/app.config.js';
import routes from './routes/index.js';

const app = express();

// Middleware
app.use(cors({
  origin: appConfig.CORS_ORIGIN
}));
app.use(express.json());

// Mount API routes
app.use('/api', routes);

// Start server
app.listen(appConfig.PORT, () => {
  console.log(`Server is running on port ${appConfig.PORT}`);
  console.log(`Environment: ${appConfig.NODE_ENV}`);
});
