import os
import boto3
import json
import scores
import scoreboard

cache_bucket_name = os.environ.get("S3_DATACACHE", "scoreboard-datacache")
s3client, s3resource = boto3.client('s3'), boto3.resource('s3')
# cache_bucket = s3resource.Bucket(cache_bucket_name)


class S3Cache(scores.Cache):
    def __init__(self,
            bucket_name: str):
        super().__init__()
        self._ramcache = {}
        self.bucket_name = bucket_name

    def has_data(self, representation: scores.DataRepresentation) -> bool:
        if representation in self._ramcache:
            return True
        # objlist = cache_bucket.objects.filter(Prefix=representation.Filename())
        # for o in objlist:
        #     print(o.key, o.size)
        # return len(list(objlist)) == 1
        response = s3client.list_objects(
            Bucket=self.bucket_name,
            Prefix=representation.filename(),
            MaxKeys=1)
        return any([_ for _ in response.get("Contents", []) if _["Key"] == representation.filename()])

    def add_data(self, representation: scores.DataRepresentation, data) -> None:
        self._ramcache[representation] = data
        s3client.put_object(
            Body=data,
            Bucket=self.bucket_name,
            Key=representation.filename())

    def get_raw(self, representation) -> str:
        if representation in self._ramcache:
            return self._ramcache[representation]
        o = s3resource.Object(cache_bucket_name, representation.filename())
        response = o.get()
        return response['Body'].read().decode("utf-8")

if __name__ == "__main__":
    c = S3Cache(cache_bucket_name)
    gl = scoreboard.GlobalListRepresentation("2020", "10")
    if c.has_data(gl):
        print("Data is cached")
    else:
        raise Exception("Not cached")
    d = c.get_raw(gl)
    print(d)

    raise Exception("This is just a module!")