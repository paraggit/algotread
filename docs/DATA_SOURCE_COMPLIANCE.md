# Data Source Compliance Guide

## Overview

AlgoTread uses only legitimate, publicly available data sources for news and market data. This document outlines each data source, its legitimacy, and compliance requirements.

## Data Sources

### 1. Zerodha Kite Connect API

**Type**: Licensed Commercial API  
**Status**: ✅ Fully Legitimate  
**Documentation**: https://kite.trade/docs/connect/v3/

**Legitimacy**:
- Official paid API service from Zerodha
- Requires API key and access token
- Governed by Zerodha's API terms of service

**Compliance Requirements**:
- Valid Zerodha trading account
- Active Kite Connect subscription
- Proper API credentials in `.env` file
- Respect rate limits (3 requests/second)

**Usage in AlgoTread**:
- Historical OHLCV data
- Live market data via WebSocket
- Order placement and management
- Portfolio and position tracking

---

### 2. Economic Times RSS Feeds

**Type**: Public RSS Feeds  
**Status**: ✅ Fully Legitimate  
**Documentation**: https://economictimes.indiatimes.com/rss.cms

**Legitimacy**:
- RSS feeds are **explicitly published** by Economic Times for public consumption
- Standard RSS 2.0 format
- No authentication required
- Intended for news aggregators and readers

**Compliance Requirements**:
- Use standard RSS parsing (feedparser)
- Respect caching to avoid excessive requests
- Attribute source properly (already implemented)
- Do not republish content commercially

**RSS Feed URLs**:
```
Markets: https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms
Stocks: https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms
```

**Usage in AlgoTread**:
- Market news headlines
- Stock-specific news
- Advisory information only (not for trade execution)

---

### 3. Google News RSS

**Type**: Public RSS Service  
**Status**: ✅ Fully Legitimate  
**Documentation**: https://support.google.com/news/

**Legitimacy**:
- Official Google News RSS search service
- Publicly documented and supported
- Standard RSS format
- No authentication required

**Compliance Requirements**:
- Use standard RSS parsing
- Respect robots.txt and rate limits
- Attribute sources properly
- Personal/non-commercial use (check Google's terms for commercial use)

**RSS Search URL**:
```
https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en
```

**Usage in AlgoTread**:
- Aggregated news from multiple sources
- Stock-specific news searches
- Market sentiment analysis
- Advisory information only

---

### 4. NSE Corporate Announcements

**Type**: Public API  
**Status**: ⚠️ Use with Caution  
**Documentation**: https://www.nseindia.com/

**Legitimacy**:
- Public data from NSE website
- Corporate announcements are public information
- API is accessible but may have undocumented terms

**Compliance Considerations**:
- NSE may have terms of service for API usage
- May require specific headers to avoid blocking
- Rate limiting may be enforced
- Consider using official NSE data feeds if available

**Current Implementation**:
```python
# Uses public API with proper headers
ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
headers = {
    'User-Agent': 'Mozilla/5.0...',
    'Accept': 'application/json',
}
```

**Recommendations**:
1. **Review NSE Terms**: Check NSE website for API usage terms
2. **Consider Alternatives**: NSE may offer official data feeds
3. **Implement Rate Limiting**: Add delays between requests
4. **Disable if Needed**: Can be disabled via `NEWS_SOURCES` config

**Usage in AlgoTread**:
- Corporate announcements
- Stock-specific events
- Advisory information only
- **Optional** - can be disabled

---

## Best Practices

### 1. Caching

All news sources implement caching to minimize requests:

```python
# Default cache settings
NEWS_CACHE_TTL=3600  # 1 hour
NEWS_MAX_AGE_HOURS=24  # Only fetch recent news
```

**Benefits**:
- Reduces load on external servers
- Faster response times
- Respects rate limits
- Lower bandwidth usage

### 2. Rate Limiting

Implement respectful rate limiting:

```python
# Configurable fetch interval
NEWS_FETCH_INTERVAL=60  # Minutes between fetches
```

**Recommendations**:
- Don't fetch more frequently than necessary
- Use cache when possible
- Implement exponential backoff on errors

### 3. Error Handling

Graceful error handling prevents hammering servers:

```python
try:
    articles = adapter.fetch()
except Exception as e:
    logger.error(f"Error fetching: {e}")
    # Continue with other sources
```

### 4. Attribution

Always attribute sources properly:

```python
article = NewsArticle(
    title=entry.title,
    source=NewsSource.ECONOMIC_TIMES,  # Proper attribution
    url=entry.link  # Link to original
)
```

---

## Terms of Service Compliance

### Economic Times

**Terms**: https://economictimes.indiatimes.com/terms-conditions  
**Key Points**:
- RSS feeds are for personal, non-commercial use
- Attribution required
- No content modification
- No republishing for commercial purposes

**AlgoTread Compliance**:
- ✅ Personal use (individual trading)
- ✅ Proper attribution
- ✅ No modification
- ✅ Advisory only (not republishing)

### Google News

**Terms**: https://www.google.com/intl/en/policies/terms/  
**Key Points**:
- Personal use permitted
- Commercial use may require license
- Attribution required
- Respect robots.txt

**AlgoTread Compliance**:
- ✅ Personal use
- ⚠️ Commercial use: Check if your trading qualifies
- ✅ Attribution via source links
- ✅ Using official RSS service

### NSE

**Terms**: https://www.nseindia.com/terms-and-conditions  
**Key Points**:
- Data is for personal use
- Commercial redistribution prohibited
- May require data subscription for commercial use
- Respect rate limits

**AlgoTread Compliance**:
- ✅ Personal use (individual trading)
- ✅ No redistribution
- ⚠️ Review terms for your specific use case
- ✅ Can be disabled if needed

---

## Disabling Data Sources

If you're concerned about any data source, you can easily disable it:

```bash
# In .env file

# Disable all news
NEWS_ENABLED=false

# Or disable specific sources
NEWS_SOURCES=economic_times,google_news  # Excludes NSE

# Or use only one source
NEWS_SOURCES=economic_times  # Only ET RSS
```

---

## Alternative Data Sources

If you prefer different sources, consider:

### Official Data Providers

1. **NSE Official Data Feeds**
   - https://www.nseindia.com/market-data
   - May require subscription
   - Fully legitimate and supported

2. **BSE Data Services**
   - https://www.bseindia.com/
   - Official exchange data
   - May require subscription

3. **MoneyControl API** (if available)
   - Popular financial news site
   - Check for official API

### News Aggregators

1. **NewsAPI.org**
   - Aggregates from 80,000+ sources
   - Free tier available
   - Official API with clear terms

2. **Alpha Vantage**
   - Financial data and news
   - Free tier available
   - Official API

---

## Legal Disclaimer

> [!IMPORTANT]
> **You are responsible for ensuring compliance with all applicable terms of service and laws.**
> 
> AlgoTread provides tools to access publicly available data, but:
> - Review each data source's terms of service
> - Ensure your usage complies with their terms
> - Consider your use case (personal vs. commercial)
> - Consult legal counsel if unsure
> - Disable sources you're uncomfortable with

---

## Audit Checklist

Before using AlgoTread in production, verify:

- [ ] You have valid Kite Connect API credentials
- [ ] You've reviewed Economic Times RSS terms
- [ ] You've reviewed Google News terms
- [ ] You've reviewed NSE terms (if using NSE source)
- [ ] Your usage is compliant with all terms
- [ ] You've configured appropriate cache settings
- [ ] You've set reasonable fetch intervals
- [ ] You understand the data is advisory only

---

## Contact and Support

If you have questions about data source compliance:

1. **Review Terms**: Check each provider's terms of service
2. **Consult Legal**: Seek legal advice for commercial use
3. **Contact Providers**: Reach out to data providers directly
4. **Disable if Unsure**: Use `NEWS_ENABLED=false` until resolved

---

## Summary

AlgoTread uses **only legitimate, publicly available data sources**:

✅ **Kite Connect**: Licensed commercial API  
✅ **Economic Times RSS**: Public RSS feeds  
✅ **Google News RSS**: Official RSS service  
⚠️ **NSE API**: Public but review terms (optional, can disable)

All implementations include:
- Proper attribution
- Caching to minimize requests
- Error handling
- Configurable rate limiting
- Easy disable options

**Recommendation**: Review each source's terms for your specific use case and disable any sources you're uncomfortable with.
