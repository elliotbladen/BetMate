import type { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const base = 'https://betmate.au';

  return [
    { url: base, lastModified: new Date(), changeFrequency: 'daily', priority: 1.0 },
    { url: `${base}/odds`, lastModified: new Date(), changeFrequency: 'hourly', priority: 1.0 },
    { url: `${base}/odds?sport=NRL`, lastModified: new Date(), changeFrequency: 'hourly', priority: 0.9 },
    { url: `${base}/odds?sport=AFL`, lastModified: new Date(), changeFrequency: 'hourly', priority: 0.9 },
    { url: `${base}/odds?sport=EPL`, lastModified: new Date(), changeFrequency: 'hourly', priority: 0.8 },
    { url: `${base}/odds?sport=CHAMPIONSHIP`, lastModified: new Date(), changeFrequency: 'hourly', priority: 0.7 },
    { url: `${base}/odds?sport=UCL`, lastModified: new Date(), changeFrequency: 'hourly', priority: 0.7 },
    { url: `${base}/research`, lastModified: new Date(), changeFrequency: 'weekly', priority: 0.6 },
    { url: `${base}/tools`, lastModified: new Date(), changeFrequency: 'weekly', priority: 0.5 },
  ];
}
