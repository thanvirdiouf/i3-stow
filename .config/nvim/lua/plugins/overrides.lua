return {
  {
    "folke/snacks.nvim",
    opts = {
      picker = {
        sources = {
          files = { cmd = "fdfind" },
          explorer = { cmd = "fdfind" },
        },
      },
    },
  },
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, { "vimdoc", "vim", "lua" })
    end,
  },
}
