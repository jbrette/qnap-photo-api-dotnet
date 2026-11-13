# QnapPhotoApi.NET
This is a .NET Web API wrapper around the QNap Photo Station api.

Provides the following capabilities.
1. `/list` - Get a list of images meeting basic criteria
   - list images
   - list albums (smart and normal)
   - list images within albums
1. Single images - This is middleware, acting as a proxy to PhotoStation on your NAS. It just forwards the response stream.
   - `/image/{imageId}` - Full size image
   - `/thumb/{imageId}` - Thumbnail of the supplied image. The size of this thumbnail depends on how thumbnails are processed in your NAS.

## Configuration 

1. Get the nuget package
1. Add configuration to your `appsettings.json`.  Username and Password are the credentials you use to login to your nas.
```csharp
"QnapApi": {
    "BaseUrl": "http://nas",
    "Username": "Rob",
    "Password": "Y0UrP455w0rd!"
}
```
3. Install in your web app/api (see below)

```csharp
// This will register CSharp API client to make the /list calls.
builder.Services.AddQnapPhotoApi(builder.Configuration);

var app = builder.Build();

// This is important to get the /image and /thumb endpoints.
app.UseQnapImageMiddleware();
```

## Usage
```csharp

app.MapGet("/list/{page:int}", async (int page, [FromServices] IPhotoStationClient qnapClient, CancellationToken cancellationToken) =>
    {
        var request = new ListRequest
        {
            MediaType = MediaType.Photos,
            SortDirection = SortDirection.Descending,
            PageNumber = page,
            PageSize = 100,
        };

        return await qnapClient.ListAsync(request, cancellationToken);
    })
    .WithName("ListPhotos")
    .WithTags("QnapPhotos")
    .WithOpenApi();

app.MapGet("/list-album-photos/{albumId}/{page:int}", async (string albumId, int page, [FromServices] IPhotoStationClient qnapClient, CancellationToken cancellationToken) =>
    {
        var request = new ListAlbumPhotosRequest()
        {
            AlbumId = albumId,
            SortDirection = SortDirection.Descending,
            Sort = Sort.DateAdded,
            PageNumber = page,
            PageSize = 100,
        };

        return await qnapClient.ListAlbumPhotosAsync(request, cancellationToken);
    })
    .WithName("ListAlbumPhotos")
    .WithTags("QnapPhotos")
    .WithOpenApi();

app.MapGet("/list-album/{page:int}", async (int page, [FromServices] IPhotoStationClient qnapClient, CancellationToken cancellationToken) =>
    {
        var request = new ListAlbumsRequest()
        {
            SortDirection = SortDirection.Descending,
            AlbumType = AlbumType.All,
            Sort = AlbumSort.Title,
            PageNumber = page,
            PageSize = 100,
        };

        return await qnapClient.ListAlbumsAsync(request, cancellationToken);
    })
    .WithName("ListAlbums")
    .WithTags("QnapPhotos")
    .WithOpenApi();
```

## Documentation

- [`architecture.md`](architecture.md): module map, NAS contracts and invariants, for anyone changing the code.
- [`python/README.md`](python/README.md): the Python port.
- [`docs/review.md`](docs/review.md): open code-review findings.
