ObjC.import('Foundation');
// Fetch articles from NetNewsWire via JXA and write them to a JSON file.
// Usage: osascript -l JavaScript nnw_fetch.js '{"unread":true,"folder":"News"}'
//
// Options (all optional):
//   account         exact account name, for example "iCloud"
//   folder          exact folder name
//   feed            case-insensitive substring of the feed name
//   unread          true (default) keeps only unread articles; false keeps read and unread
//   starred         true keeps only starred articles
//   sinceHours      only articles published or arrived in the last N hours
//   limit           cap on articles written (newest first); "total" still reports the full count
//   excludeFolders  array of folder names to skip
//   out             output path (default /tmp/nnw/articles.json)
function run(argv) {
  const o = Object.assign({
    account: null, folder: null, feed: null,
    unread: true, starred: false,
    sinceHours: null, limit: null,
    excludeFolders: [], out: '/tmp/nnw/articles.json'
  }, argv[0] ? JSON.parse(argv[0]) : {});

  const fm = $.NSFileManager.defaultManager;
  const dir = ObjC.unwrap($(o.out).stringByDeletingLastPathComponent);
  fm.createDirectoryAtPathWithIntermediateDirectoriesAttributesError(dir, true, $(), $());

  const nnw = Application('NetNewsWire');
  const hasSinceHours = o.sinceHours !== null && o.sinceHours !== undefined;
  const cutoff = hasSinceHours ? new Date(Date.now() - o.sinceHours * 3600e3) : null;
  const items = [], errors = [];

  for (const a of nnw.accounts()) {
    const an = a.name();
    if (o.account && an !== o.account) continue;

    const groups = [];
    if (!o.folder) groups.push({ folder: '(top level)', feeds: a.feeds() });
    for (const fo of a.folders()) {
      const fn = fo.name();
      if (o.folder && fn !== o.folder) continue;
      if (o.excludeFolders.includes(fn)) continue;
      groups.push({ folder: fn, feeds: fo.feeds() });
    }

    for (const g of groups) for (const f of g.feeds) {
      let fname = '';
      try {
        fname = f.name();
        if (o.feed && !fname.toLowerCase().includes(o.feed.toLowerCase())) continue;
        const arts = f.articles;
        const reads = arts.read(), stars = arts.starred();
        const idx = [];
        for (let j = 0; j < reads.length; j++) {
          if (o.unread && reads[j]) continue;
          if (o.starred && !stars[j]) continue;
          idx.push(j);
        }
        if (!idx.length) continue;
        const pub = arts.publishedDate(), arr = arts.arrivedDate();
        const keep = cutoff ? idx.filter(j => pub[j] >= cutoff || arr[j] >= cutoff) : idx;
        if (!keep.length) continue;
        const titles = arts.title(), urls = arts.url(), html = arts.html();
        for (const j of keep) items.push({
          account: an, folder: g.folder, feed: fname, title: titles[j], url: urls[j],
          read: reads[j], starred: stars[j],
          published: String(pub[j] || arr[j]), html: html[j]
        });
      } catch (e) { errors.push({ feed: fname, error: String(e) }); }
    }
  }

  items.sort((x, y) => new Date(y.published) - new Date(x.published));
  const hasLimit = o.limit !== null && o.limit !== undefined;
  const res = hasLimit ? items.slice(0, o.limit) : items;
  $(JSON.stringify({
    fetchedAt: new Date().toISOString(), filters: o,
    total: items.length, errors: errors, articles: res
  })).writeToFileAtomicallyEncodingError(o.out, true, $.NSUTF8StringEncoding, $());
  return 'wrote ' + res.length + ' of ' + items.length + ' matching articles, ' +
         errors.length + ' feed errors -> ' + o.out;
}
