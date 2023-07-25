script_version('0.9')

function update()
  local raw = 'https://raw.githubusercontent.com/sieeki/auto-upd/main/update.json'
  local dlstatus = require('moonloader').download_status
  local requests = require('requests')
  local f = {}
  function f:getLastVersion()
      local response = requests.get(raw)
      if response.status_code == 200 then
          return decodeJson(response.text)['last']
      else
          return 'UNKNOWN'
      end
  end
  function f:download()
      local response = requests.get(raw)
      if response.status_code == 200 then
          downloadUrlToFile(decodeJson(response.text)['url'], thisScript().path, function (id, status, p1, p2)
              print('Скачиваю '..decodeJson(response.text)['url']..' в '..thisScript().path)
              if status == dlstatus.STATUSEX_ENDDOWNLOAD then
                  sampAddChatMessage('Скрипт обновлен, перезагрузка...', -1)
                  thisScript():reload()
              end
          end)
      else
          sampAddChatMessage('Ошибка, невозможно установить обновление, код: '..response.status_code, -1)
      end
  end
  return f
end

function main()
  while not isSampAvailable() do wait(0) end
  local lastver = update():getLastVersion()
  sampAddChatMessage('Скрипт загружен, версия: '..lastver, -1)
  if thisScript().version ~= lastver then
      sampRegisterChatCommand('scriptupd', function()
          update():download()
      end)
      sampAddChatMessage('Вышло обновление скрипта ('..thisScript().version..' -> '..lastver..'), введите /scriptupd для обновления!', -1)
  end
  wait(-1)
end
