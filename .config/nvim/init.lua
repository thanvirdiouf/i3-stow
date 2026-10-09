-- Older Kitty/Alacritty versions send some key releases as extra key presses.
-- Keep enhanced key encoding, but stop requesting release events.
vim.api.nvim_create_autocmd({ "UIEnter", "VimResume" }, {
  group = vim.api.nvim_create_augroup("terminal_keyboard_workaround", { clear = true }),
  callback = vim.schedule_wrap(function()
    vim.api.nvim_ui_send("\27[=2;3u")
  end),
})

-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")
