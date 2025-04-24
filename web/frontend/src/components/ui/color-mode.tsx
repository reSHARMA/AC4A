import { IconButton, useColorMode } from '@chakra-ui/react'
import { LuMoon, LuSun } from 'react-icons/lu'

export const ColorModeButton = () => {
  const { colorMode, toggleColorMode } = useColorMode()

  return (
    <IconButton
      aria-label="Toggle color mode"
      icon={colorMode === 'light' ? <LuMoon /> : <LuSun />}
      onClick={toggleColorMode}
      variant="ghost"
      size="md"
    />
  )
} 