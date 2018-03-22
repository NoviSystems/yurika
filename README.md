# Yurika: Unstructured Text Analytics Platform

<!-- [![Build Status](https://travis-ci.org/ITNG/yurika.svg?branch=master)](https://travis-ci.org/ITNG/yurika) -->

## The Augmented Intelligence Process

Our process consists of five steps:

- Gathering
- Filtering
- Annotating
- Restructuring
- Visualizing

### Gathering
Crawling the web is our basic method of gathering unstructured data. We start with a list
of URLs, then scrape the pages, parse them into an index-able format, and store them off
for later use. In this step, we also collect any already structured data that we may find
useful, such as geolocations or historical weather for an area. This data is stored away
until the Restructuring step.

### Filtering
Because our crawling is unspecific and grabs everything it sees on the pages we give it,
we end up with a lot of noise in our initial dataset. We whittle the dataset down a little
by creating Mindmaps or PESTLE (Political, Economical, Social, Technical, Legal,
Environmental) trees that we can use to query for specific topics within our collected
webpages.

### Annotating
Annotating is a second run of culling our data to gain insight into our question. We can
use regular expression matching to pull out a word from a sentence or a sentence from a
paragraph, to find names, dates, or money (specific values or in general), or any number
of other types of information that are relevant to the question being asked.

### Restructuring
After annotating the data, we export it into a structured format (usually csv or json) to
be stored in a SQL database. Typically, each type of annotation we have created is given
its own table, along with the tables of pre-structured data we gathered in the first step.

### Visualizing
Where the magic happens. Now that we have all of our data in an easily-managed format, we
can analyze the relationships between our annotations and structured data, and create a
Truth Table with adjustable weighted values to craft an answer to our question that's
backed by the data.
