import requests
import datetime
import json
import os
from tqdm import tqdm


def get_token_and_id(file_name):
    """Функция для чтения токена и ID пользователя (из передаваемого файла - 1 строка токен, 2 ID"""
    with open(os.path.join(os.getcwd(), file_name), 'r') as token_file:
        token = token_file.readline().strip()
        id_one = token_file.readline().strip()
    return [token, id_one]


def find_max_photo_dpi(dict_return_from_search):
    """Функция возвращает размер и ссылку на фото максимального размера"""
    max_dpi = 0
    max_elem = 0
    for elem in range(len(dict_return_from_search)):
        file_dpi = dict_return_from_search[elem].get('width') * dict_return_from_search[elem].get('height')
        if file_dpi > max_dpi:
            max_dpi = file_dpi
            max_elem = elem
    return dict_return_from_search[max_elem].get('url'), dict_return_from_search[max_elem].get('type')


def convert_time(time_unix):
    """"Функуия преобразовывает дату загрузки фото в человеко-читаемый вид"""
    time_bc = datetime.datetime.fromtimestamp(time_unix)
    str_time = time_bc.strftime('%Y-%m-%d time %H-%M-%S')
    return str_time


class Vkontakte:
    def __init__(self, token_list, version='5.131'):
        """Метод получения параметров для запроса ВК"""
        self.token = token_list[0]
        self.id = token_list[1]
        self.version = version
        self.start_params = {'access_token': self.token, 'v': self.version}
        self.json, self.export_dict = self._sort_info()

    def _get_photo_info(self):
        """Метод получения массива фотографий и его количества"""
        url = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': self.id,
                  'album_id': 'profile',
                  'rev': 1,
                  'extended': 1,
                  'photo_sizes': 1}

        photo_info = requests.get(url=url, params={**self.start_params, **params}).json()['response']
        return photo_info['count'], photo_info['items']

    def _get_params_photo(self):
        """метод получения словаря с параметрами фото юзера"""
        photo_count, photo_items = self._get_photo_info()
        result = {}
        for i in range(photo_count):
            likes_count = photo_items[i]['likes']['count']
            url_download, picture_size = find_max_photo_dpi(photo_items[i]['sizes'])
            time_warp = convert_time(photo_items[i]['date'])
            new_value = result.get(likes_count, [])
            new_value.append({'likes_count': likes_count,
                              'add_name': time_warp,
                              'url_picture': url_download,
                              'size': picture_size})
            result[likes_count] = new_value
        return result

    def _sort_info(self):
        """Метод получения словаря с параметрами фото и JSON для выгрузки"""
        json_list = []
        sorted_dict = {}
        pic_dict = self._get_params_photo()
        count = 0
        for elem in pic_dict.keys():
            for value in pic_dict[elem]:
                if len(pic_dict[elem]) == 1:
                    file_name = f'{value["likes_count"]}.jpeg'
                else:
                    file_name = f'{value["likes_count"]} {value["add_name"]}.jpeg'
                json_list.append({'file name': file_name, 'size': value['size']})
                if value['likes_count'] == 0:
                    sorted_dict[file_name] = pic_dict[elem][count]['url_picture']
                    count += 1
                else:
                    sorted_dict[file_name] = pic_dict[elem][0]['url_picture']
        return json_list, sorted_dict


class Yandex:
    def __init__(self, folder_name, token_list, num=5):
        """Метод получения параметров для загрузки на я-диск """
        self.token = token_list[0]
        self.added_files_count = num
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.headers = {'Authorization': self.token}
        self.folder = self._create_folder(folder_name)

    def _create_folder(self, folder_name):
        """Метод создания папки для загрузки на Я-диске"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        if requests.get(url=url, headers=self.headers, params=params).status_code != 200:
            requests.put(url=url, headers=self.headers, params=params)
            print(f'\nПапка "{folder_name}" создана в корнев каталога Яндекс диска\n')
        else:
            print(f'\nПапка "{folder_name}" уже существует. Одноименные файлы не будут скопированы.\n')
        return folder_name

    def _get_upload_link(self, folder_name):
        upload_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': folder_name}
        resource = requests.get(url=upload_url, headers=self.headers, params=params).json()['_embedded']['items']
        link_list = []
        for elem in resource:
            link_list.append(elem['name'])
        return link_list

    def create_copy(self, dict_files):
        """Метод загрузки фото на я-диск"""
        files_in_folder = self._get_upload_link(self.folder)
        copy_count = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.added_files_count))):
            if copy_count < self.added_files_count:
                if key not in files_in_folder:
                    params = {'path': f'{self.folder}/{key}',
                              'url': dict_files[key],
                              'overwrite': 'false'}
                    requests.post(url=self.url, headers=self.headers, params=params)
                    copy_count += 1
                else:
                    print(f'Файл "{key}" уже существует')
            else:
                break
        print(f'\nОперация выполнена, новых файлов загружено: {copy_count}'
              f'\nВсего файлов в альбоме пользователя VK: {len(dict_files)}')


if __name__ == '__main__':
    tokenVK = 'vk_token.txt'
    tokenYandex = 'ya_token.txt'
    my_VK = Vkontakte(get_token_and_id(tokenVK))

    with open('VK_photo.json', 'w') as outfile:
        json.dump(my_VK.json, outfile)

    my_yandex = Yandex('Ya copy from VK', get_token_and_id(tokenYandex), 5)
    my_yandex.create_copy(my_VK.export_dict)
