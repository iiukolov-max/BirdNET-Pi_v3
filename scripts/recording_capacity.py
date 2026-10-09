"""Storage forecast: current settings first, valid live measurements when available."""
import math

def recording_rate(conf, measured=None):
    fmt=conf.get('AUDIOFMT','flac')
    seconds=int(conf.get('RECORDING_LENGTH','15'))
    channels=int(conf.get('CHANNELS','1'))
    if seconds<=0 or channels<=0:raise ValueError('Invalid recording settings')
    # FLAC size varies with the signal: 60% of 48kHz/16bit PCM is an estimate,
    # not an observed compression ratio. Lossy formats use provisional bitrates.
    nominal={'flac':48000*2*channels*.6,'wav':48000*2*channels,
             'mp3':(128000 if channels==1 else 192000)/8,
             'ogg':80000*channels/8,'opus':64000*channels/8}
    rate=nominal.get(fmt)
    if rate is None:raise ValueError('Unknown recording format')
    source='format_estimate'
    measured=measured or {}
    value=measured.get('bytes_per_second')
    if (measured.get('has_signal') is True and measured.get('format')==fmt
            and measured.get('segment_seconds')==seconds and measured.get('channels')==channels
            and measured.get('sample_rate')==48000 and isinstance(value,(int,float))
            and math.isfinite(value) and value>0):
        rate=value;source='measured'
    # Per-file headers and filesystem block allocation also consume space.
    file_bytes=math.ceil((rate*seconds+(0 if source=='measured' else 8192))/4096)*4096
    return {'bytes_per_second':file_bytes/seconds,'file_bytes':file_bytes,
            'segment_seconds':seconds,'estimate_source':source}

def capacity(conf,disk,measured=None):
    threshold=int(conf.get('ARCHIVE_MAX_USED_PERCENT','85'))
    # Cleanup starts at its trigger reserve; its target reserve is separate.
    available=max(0,disk.free-max(disk.total*(100-threshold)/100,512*1024**2))
    rate=recording_rate(conf,measured)
    return {'free_bytes':disk.free,'total_bytes':disk.total,'max_used_percent':threshold,
            'available_before_cleanup_bytes':int(available),'estimated_files':int(available/rate['file_bytes']),
            'estimated_days':available/rate['bytes_per_second']/86400,**rate}
