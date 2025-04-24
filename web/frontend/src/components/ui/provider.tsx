"use client"

import { PropsWithChildren } from 'react'
import { ColorModeProvider, ColorModeScript } from '@chakra-ui/react'
import theme from '../../theme'

export const Provider = ({ children }: PropsWithChildren) => {
  return (
    <>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <ColorModeProvider options={theme.config}>
        {children}
      </ColorModeProvider>
    </>
  )
}
