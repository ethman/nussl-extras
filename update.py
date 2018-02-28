#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import hashlib
import datetime

import librosa
import bs4


def main():

    # ---------- Audio ----------
    audio_json = 'audio_metadata.json'
    audio_dir = os.path.join('assets', 'audio')
    audio_ext = ['wav', 'mp3', 'ogg', 'flac', 'm4a', 'aif', 'aiff']
    audio_metadata_key = 'nussl Audio File metadata'
    audio_metadata_reqs = {'file_description': None, 'audio_attributes': None,
                           'file_length_seconds': _audio_length_sec, 'date_added': _cur_date,
                           'date_modified': _cur_date, 'file_size_bytes': os.path.getsize,
                           'file_size': _human_readable_file_size, 'file_hash': _hash_file}

    audio_metadata = update_metadata_file(audio_json, audio_dir, audio_ext, audio_metadata_key, audio_metadata_reqs)

    # ---------- Benchmarks ----------
    benchmark_json = 'benchmark_metadata.json'
    benchmark_dir = os.path.join('assets', 'benchmarks')
    benchmark_ext = ['npy', 'mat', 'wav']
    benchmark_metadata_key = 'nussl Benchmarks metadata'
    benchmark_metadata_reqs = {'file_description': None, 'date_added': _cur_date, 'date_modified': _cur_date,
                               'for_class': None, 'file_size': _human_readable_file_size, 'file_hash': _hash_file}

    benchmark_metadata = update_metadata_file(benchmark_json, benchmark_dir, benchmark_ext,
                                              benchmark_metadata_key, benchmark_metadata_reqs)

    # ---------- Models ----------
    model_json = 'model_metadata.json'
    model_dir = os.path.join('assets', 'models')
    model_ext = ['h5', 'hdf5']
    model_metadata_key = 'nussl Models metadata'
    model_metadata_reqs = {'file_description': None, 'date_added': _cur_date, 'date_modified': _cur_date,
                           'file_size_bytes': os.path.getsize,
                           'file_size': _human_readable_file_size, 'file_hash': _hash_file}

    model_metadata = update_metadata_file(model_json, model_dir, model_ext, model_metadata_key, model_metadata_reqs)

    # ---------- Update index.html ----------
    base = '/nussl-extras/assets'
    audio_names_paths = {a['file_name']: os.path.join(base, 'audio', a['file_name'])
                         for a in audio_metadata[audio_metadata_key]}
    benchmark_names_paths = {a['file_name']: os.path.join(base, 'benchmarks', a['file_name'])
                             for a in benchmark_metadata[benchmark_metadata_key]}
    model_names_paths = {a['file_name']: os.path.join(base, 'models', a['file_name'])
                         for a in model_metadata[model_metadata_key]}
    update_html(audio_names_paths, benchmark_names_paths, model_names_paths)


# -------------------------------------------------
#               HELPER FUNCTIONS
# -------------------------------------------------

def _audio_length_sec(file_path):
    y, sr = librosa.load(file_path)
    return librosa.get_duration(y=y, sr=sr)


def _cur_date(file_path=None):
    return datetime.datetime.now().strftime('%Y-%m-%d')


def _human_readable_file_size(file_path, suffix='B'):
    num = os.path.getsize(file_path)

    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def _hash_file(file_path, chunk_size=65535):
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as fpath_file:
        for chunk in iter(lambda: fpath_file.read(chunk_size), b''):
            hasher.update(chunk)

    return hasher.hexdigest()


# -------------------------------------------------
#           METADATA UPDATE FUNCTION
# -------------------------------------------------

def update_metadata_file(metadata_file, assets_folder, allowed_exts, metadata_key, metadata_reqs_dict):
    """
    Will update a metadata json file (`metadata_file`) by polling the `assets_folder`.
    :param metadata_file:
    :param assets_folder:
    :param allowed_exts:
    :param metadata_key:
    :param metadata_reqs_dict:
    :return:
    """

    # Open the metadata file
    try:
        with open(metadata_file, 'r') as a:
            metadata_dict = json.load(a)[metadata_key]
    except ValueError:
        print('Could not open metadata file {}!'.format(metadata_file))
        metadata_dict = []

    # Get list of files in assets_folder, and compare to metadata
    asset_files = [file_ for file_ in os.listdir(assets_folder) if file_.split(os.extsep)[1] in allowed_exts]
    metadata_files = [entry['file_name'] for entry in metadata_dict]
    new_files = [f for f in asset_files if f not in metadata_files]

    if len(new_files) < 0:
        print('Detected {} new files: {}.'.format(len(new_files), ', '.join(new_files)))

    # Update metadata with data from new files
    for file_ in new_files:
        path = os.path.join(assets_folder, file_)
        new_entry = {'file_name': file_}

        for field, func in metadata_reqs_dict.items():
            if callable(func):
                new_entry.update({field: func(path)})

        metadata_dict.append(new_entry)

    # Check existing metadata for errors
    for i, data in enumerate(metadata_dict):

        if 'file_name' not in data:
            print('\033[91mEntry {} is missing field file_name! Cannot fix automatically!\033[0m')
            continue

        # Check for all of the required keys
        diff = set(metadata_reqs_dict.keys()) - set(data.keys())  # Check for any missing keys
        diff.update(k for k in data.keys() if not data[k])  # Check if any values are empty

        if diff:
            print('Entry {} (\033[91m{}\033[0m) is missing '
                  'the following fields: \033[91m{}\033[0m!'.format(i, data['file_name'], ', '.join(diff)))

            for field in diff:
                path = os.path.join(assets_folder, data['file_name'])
                try:
                    data[field] = metadata_reqs_dict[field](path)
                    print('Fixed {}'.format(field))
                except:
                    data[field] = ''
                    print('\tCan\'t to understand field {}! Skipping...'.format(field))

    # Write metadata file
    metadata_dict = {metadata_key: metadata_dict, 'last_updated': datetime.datetime.now().strftime('%Y-%m-%d')}
    with open(metadata_file, 'w') as a:
        json.dump(metadata_dict, a, indent=2, sort_keys=True)

    return metadata_dict

# -------------------------------------------------
#            HTML UPDATE FUNCTION
# -------------------------------------------------


def update_html(audio_files, benchmark_files, model_files):

    with open('index.html', 'r') as index_html:
        soup = bs4.BeautifulSoup(index_html.read(), 'lxml')

    l = [('audio-list', audio_files), ('benchmark-list', benchmark_files), ('model-list', model_files)]
    for id, file_list in l:
        # Get the <li> for the relevant list then the inner <ul>
        outer_li = soup.find('li', {'id': id})
        ul = outer_li.find('ul')

        # Remove everything already in the <ul>
        [li.extract() for li in ul.findChildren()]

        # Populate the <ul> with new tags
        for fn, loc in file_list.items():
            li = soup.new_tag('li')
            a = soup.new_tag('a', href=loc)
            a.string = fn
            li.append(a)
            ul.append(li)

    with open('index.html', 'w') as index_html:
        index_html.write(soup.prettify())


if __name__ == '__main__':
    main()