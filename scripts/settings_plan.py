"""Explicit settings dependencies shared by fast and background application."""
HOT_KEYS = {'BIRDWEATHER_ID', 'REMOTE_ANALYSIS_BATCH',
            'APPRISE_NOTIFICATION_TITLE', 'APPRISE_NOTIFY_EACH_DETECTION',
            'APPRISE_NOTIFY_NEW_SPECIES', 'APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY',
            'APPRISE_WEEKLY_REPORT', 'APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES',
            'APPRISE_ONLY_NOTIFY_SPECIES_NAMES', 'APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2'}
FAST_KEYS = HOT_KEYS | {'SITE_NAME','INFO_SITE','IMAGE_PROVIDER','FLICKR_API_KEY',
    'FLICKR_FILTER_EMAIL','CUSTOM_IMAGE','CUSTOM_IMAGE_TITLE','SILENCE_UPDATE_INDICATOR',
    'AUTOMATIC_UPDATE','FULL_DISK','PURGE_THRESHOLD','MAX_FILES_SPECIES',
    'ARCHIVE_MAX_USED_PERCENT','FREQSHIFT_TOOL','FREQSHIFT_PITCH',
    'FREQSHIFT_RECONNECT_DELAY','RARE_SPECIES_THRESHOLD'}
AUXILIARY = {
    'chart_viewer': {'COLOR_SCHEME','DATABASE_LANG'},
    'livestream': {'ICE_PWD','REC_CARD','CHANNELS','MICROPHONE_GAIN_100','RTSP_STREAM','RTSP_STREAM_TO_LIVESTREAM',
                   'ACTIVATE_FREQSHIFT_IN_LIVESTREAM','FREQSHIFT_HI','FREQSHIFT_LO',
                   'LogLevel_LiveAudioStreamService'},
    'spectrogram_viewer': {'RAW_SPECTROGRAM','RECORDING_LENGTH','LogLevel_SpectrogramViewerService'},
}


def fast_keys(config):
    keys = set(FAST_KEYS)
    # These settings have no running consumer in archive mode's optional services.
    if config.get('OPERATION_MODE','normal') == 'archive':
        keys.update({'COLOR_SCHEME','LogLevel_BirdnetRecordingService',
                     'LogLevel_LiveAudioStreamService','LogLevel_SpectrogramViewerService',
                     'RTSP_STREAM_TO_LIVESTREAM','ACTIVATE_FREQSHIFT_IN_LIVESTREAM',
                     'FREQSHIFT_HI','FREQSHIFT_LO'})
        keys.update({'SERVICE_ALLOW_LIVE_AUDIO','SERVICE_ALLOW_STATISTICS','SERVICE_ALLOW_CHARTS',
                     'SERVICE_ALLOW_SPECTROGRAMS','SERVICE_ALLOW_LOG','SERVICE_ALLOW_TERMINAL'})
    if config.get('ANALYSIS_BACKEND','local') == 'local':keys.add('REMOTE_ANALYSIS_IP')
    return keys
