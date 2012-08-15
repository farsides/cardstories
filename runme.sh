PYTHONPATH=.:etc/cardstories twistd --nodaemon cardstories \
    --static $(pwd)/static --port 5000 --interface 0.0.0.0 \
    --db /tmp/cardstories.sqlite \
    --plugins-dir plugins \
    --plugins-libdir /tmp \
    --plugins-logdir log/ \
    --plugins-confdir tests \
    --plugins 'auth chat activity table' \
    --plugins-pre-process 'auth chat' \
    --plugins-post-process 'table'