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
}
