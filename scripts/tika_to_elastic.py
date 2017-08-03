import elasticsearch
import tika
import multiprocessing as mp, os

ES_URL = 'http://10.36.1.3:9200/'
DATA_DIR = 'data/'

def process(line):
    # 
    pass

#### from http://www.blopig.com/blog/2016/08/processing-large-files-using-python/
def process_wrapper(file_name, chunk_start, chunk_size):
    with open(file_name) as f:
        f.seek(chunk_start)
        lines = f.read(chunk_size).splitlines()
        for line in lines:
            process(line)

def chunkify(file_name, size=1024*1024):
    file_end = os.path.getsize(file_name)
    with open(file_name, 'r') as f:
        chunk_end = f.tell()

    while True:
        chunk_start = chunk_end
        f.seek(size,1)
        f.readline()
        chunk_end = f.tell()
        yield chunk_start, chunk_end - chunk_start
        if chunk_end > file_end:
            break

def run_jobs(file_name):
    with mp.Pool(cores) as pool:
        jobs = []
    
        for chunk_start, chunk_size in chunkify(file_name):
            jobs.append(pool.apply_async(process_wrapper,(chunk_start,chunk_size)))

        for job in jobs:
            job.get()

####


def create_nutch_index(client):
    i_client = elasticsearch.client.IndicesClient(client=client)
    if i_client.exists('nutch'):
        return
    
    body = {
      "mappings" : {
        "doc" : {
          "properties" : {
            "anchor" : { "type" : "string" },
            "boost" : { "type" : "string" },
            "cache" : { "type" : "string" },
            "content" : { "type" : "string" },
            "digest" : { "type" : "string" },
            "host" : { "type" : "string" },
            "id" : { "type" : "string" },
            "title" : { "type" : "string" },
            "tstamp" : {
              "type" : "date",
              "format" : "strict_date_optional_time||epoch_millis"
            },
            "url" : { "type" : "string" }
          }
        }
      }
    }
    i_client.create(index='nutch', body=body)


for root, dirs, files in os.walk(DATA_DIR):
    for f in files:
        filepath = os.sep.join([root, f])
        


client = elasticsearch.Elasticsearch([ES_URL], elasticsearch.RequestsHttpConnection)


